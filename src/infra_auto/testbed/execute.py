import os
import difflib
import requests
from typing import List, Dict, Optional
from pprint import pprint

from nornir import InitNornir
from nornir.core.task import Result, Task
from nornir_napalm.plugins.connections import CONNECTION_NAME as NAPALM_CONNECTION_NAME
from nornir_netmiko import CONNECTION_NAME as NETMIKO_CONNECTION_NAME

from config_utils import filter_config

# API Configuration
API_BASE_URL = os.environ.get("TESTBED_INVENTORY_API", "http://10.192.4.172:8000")


def ignore_config_diff_line(line: str) -> bool:
    """
    Ignore lines that start with !Time: or are empty
    """
    return (
        line.startswith("!Time: ")  # IOS-XE
        or line.startswith("!Running configuration")  # NXOS
        or line.startswith("!! Last configuration")  # IOS-XR
    )


def get_available_machines() -> List[Dict]:
    """
    Get list of available machines from the API
    """
    try:
        response = requests.get(f"{API_BASE_URL}/machines")
        response.raise_for_status()
        data = response.json()
        return data.get("machines", [])
    except requests.RequestException as e:
        print(f"Error fetching machines: {e}")
        return []


def reserve_machine(vendor: str, model: str, version: str) -> Optional[Dict]:
    """
    Reserve a machine with specified vendor, model, and version
    Returns the reserved machine details or None if reservation fails
    """
    try:
        url = f"{API_BASE_URL}/reserve/{vendor}/{model}/{version}"
        response = requests.post(url)
        response.raise_for_status()
        machine = response.json()
        print(f"Reserved machine: {machine.get('serial')} ({machine.get('ip')})")
        return machine
    except requests.RequestException as e:
        print(f"Error reserving machine: {e}")
        return None


def release_machine(serial: str) -> bool:
    """
    Release a machine by its serial number
    Returns True if release was successful, False otherwise
    """
    try:
        url = f"{API_BASE_URL}/release/{serial}"
        response = requests.post(url)
        response.raise_for_status()
        result = response.json()
        print(f"Released machine: {serial}")
        return True
    except requests.RequestException as e:
        print(f"Error releasing machine {serial}: {e}")
        return False


def platform_to_vendor_model(platform: str) -> tuple:
    """
    Map platform name to vendor and model
    """
    platform_mapping = {
        "ios": ("cisco", "c8k"),
        "iosxe": ("cisco", "c8k"),
        "nxos_ssh": ("cisco", "n9k"),
        "iosxr": ("cisco", "xrv"),
    }
    return platform_mapping.get(platform.lower(), ("cisco", "unknown"))


def diff_cfg(old_cfg: str, new_cfg: str) -> str:
    """
    Compare two configurations and return the diff
    """
    old_cfg_line_by_line = [
        line for line in old_cfg.splitlines() if not ignore_config_diff_line(line)
    ]
    new_cfg_line_by_line = [
        line for line in new_cfg.splitlines() if not ignore_config_diff_line(line)
    ]

    diff = ""
    for line in difflib.unified_diff(
        old_cfg_line_by_line, new_cfg_line_by_line, lineterm=""
    ):
        line = line.strip()
        if len(line) > 0:
            diff += line + "\n"
    return diff


def run_preconfig_check(task: Task, extra_commands: List[str] = []) -> Result:
    config_result = ""
    print("Running pre-configuration check...")
    target_host = task.host
    print("Target host:", target_host.name)

    platform = target_host.platform
    print("Platform:", platform)

    version = target_host.data["version"]
    print("Version:", version)

    # 2. Reserve a test device from the API
    vendor, model = platform_to_vendor_model(platform)

    # Get available machines to find a matching version
    machines = get_available_machines()
    available_machine = None
    for machine in machines:
        if (
            machine.get("vendor") == vendor
            and machine.get("model") == model
            and machine.get("status") == "available"
        ):
            available_machine = machine
            break

    if not available_machine:
        return Result(
            host=task.host,
            result=f"No available test machine found for platform {platform} (vendor: {vendor}, model: {model})",
            changed=False,
            failed=True,
        )

    # Reserve the machine
    reserved_machine = reserve_machine(
        available_machine["vendor"],
        available_machine["model"],
        available_machine["version"],
    )

    pprint(reserved_machine)

    if not reserved_machine:
        return Result(
            host=task.host,
            result=f"Failed to reserve test machine for platform {platform}",
            changed=False,
            failed=True,
        )

    machine_serial = reserved_machine.get("serial")
    machine_hostname = reserved_machine.get("hostname")
    machine_mgmt_ip = reserved_machine.get("mgmt_ip")
    machine_mgmt_netmask = reserved_machine.get("netmask")
    machine_mgmt_gateway = reserved_machine.get("default_gateway")

    print("Reserved machine serial:", machine_serial)

    # write reserved machine to hosts.yaml
    random_host_filename = "/tmp/hosts_{}.yaml".format(machine_serial)
    with open(random_host_filename, "w") as f:
        f.write(f"""
{machine_hostname}:
  hostname: {machine_mgmt_ip}
  platform: {platform}
  groups:
    - {model}
        """)

    target_cfg_file = "cfg/{}.cfg".format(target_host.name)
    with open(target_cfg_file, "r") as f:
        target_config_lines = f.readlines()
        # remove \n from each line
        target_config_lines = [line.rstrip("\n") for line in target_config_lines]

    # 1. generate sanitized config
    sanitized_config = filter_config(
        platform,
        target_config_lines,
        {
            "hostname": machine_hostname,
            "mgmt_ip": machine_mgmt_ip,
            "netmask": machine_mgmt_netmask,
            "default_gateway": machine_mgmt_gateway,
        },
    )

    print("Sanitized config: ", "\n".join(sanitized_config))

    try:
        # 3. Create a dynamic Nornir inventory with the reserved machine
        # test_inventory_config = "testbed/nornir.yaml"
        # test_nr = InitNornir(config_file=test_inventory_config)

        test_nr = InitNornir(
            inventory={
                "plugin": "SimpleInventory",
                "options": {
                    "defaults_file": "inventory/defaults.yaml",
                    "group_file": "inventory/groups.yaml",
                    "host_file": random_host_filename,
                },
            }
        )

        print(test_nr.inventory.hosts)

        # Find or create a test device entry
        # Try to find existing device with matching platform
        test_device = test_nr.inventory.hosts["tndo-n9k-2"]

        if not test_device:
            return Result(
                host=task.host,
                result=f"No test device configuration found for platform {platform} in testbed inventory",
                changed=False,
                failed=True,
            )

        print(
            "Test config on {} (Reserved: {})".format(test_device.name, machine_serial)
        )

        # 5. use NAPALM to load init config and sanitize config
        test_con = test_device.get_connection(NAPALM_CONNECTION_NAME, test_nr.config)
        netmiko_test_con = test_device.get_connection(
            NETMIKO_CONNECTION_NAME, test_nr.config
        )

        try:
            test_con.load_replace_candidate(config="\n".join(sanitized_config))
            diff = test_con.compare_config()
            config_result += "Configuration diff:\n"
            config_result += diff + "\n"
            print(diff)
            test_con.commit_config()
            rollback_log_verify = netmiko_test_con.send_command(
                "show rollback log verify"
            )
            config_result += "Rollback log verify:\n"
            config_result += rollback_log_verify + "\n"
        except Exception:
            rollback_log_verify = netmiko_test_con.send_command(
                "show rollback log verify"
            )
            rollback_log_exec = netmiko_test_con.send_command("show rollback log exec")
            config_result += "Rollback log verify:\n"
            config_result += rollback_log_verify + "\n"
            config_result += "Rollback log exec:\n"
            config_result += rollback_log_exec + "\n"

        return Result(
            host=task.host,
            result=config_result,
            # diff=config_diff,
            changed=True,
        )

    finally:
        # 8. Always release the machine after testing
        if machine_serial:
            print("Releasing machine:", machine_serial)
            release_machine(machine_serial)
