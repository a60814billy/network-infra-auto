import os
import re
import ipaddress
from typing import Optional, List

import difflib

from jinja2 import Template
from nornir import InitNornir
from nornir.core.task import Task, Result

from .sanitize_config import sanitize_ios_config, sanitize_nxos_config
from nornir.core.filter import F
from nornir_netmiko import CONNECTION_NAME as NETMIKO_CONNECTION_NAME
from nornir_napalm.plugins.connections import CONNECTION_NAME as NAPALM_CONNECTION_NAME

# Configure logging for Nornir initialization within the task (use cautiously)
template_dir_path = os.path.join(os.path.dirname(__file__), "templates/")

template_path = {
    "ios": "ios_snmp_config.j2",
    "nxos_ssh": "nxos_snmp_config.j2",
    "iosxr": "iosxr_snmp_config.j2",
}


def get_snmp_vars_from_host(host) -> dict:
    snmp_vars = host.get("baseline_snmp", {})
    if "snmp_access_list" in snmp_vars:
        snmp_vars["_snmp_acl_allow_networks"] = []

        for access_list in snmp_vars["snmp_access_list"]:
            ip = ipaddress.ip_network(access_list)
            snmp_vars["_snmp_acl_allow_networks"].append(
                {"network": str(ip.network_address), "wildcard": str(ip.hostmask)}
            )
    return snmp_vars


def filter_hosts(host):
    return "baseline_snmp" in host.keys()


def generate_snmp_config(platform: str, snmp_vars: dict) -> list[str]:
    if platform not in template_path:
        raise ValueError(f"Unsupported platform: {platform}")

    template_file = template_path[platform]
    template_full_path = os.path.join(template_dir_path, template_file)

    try:
        with open(template_full_path, "r") as f:
            template_content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Template file not found: {template_full_path}")

    snmp_config_template = Template(template_content)

    # Render the configuration using Jinja2
    rendered_config = snmp_config_template.render(**snmp_vars).splitlines()

    # Filter out comments and empty lines
    commend_regex = re.compile(r"(^\s*!.*)|(^\s*$)")
    filtered_config = [
        line for line in rendered_config if not commend_regex.match(line)
    ]
    return filtered_config


# --- Pre-config Check Helper Functions ---


def ignore_config_diff_line(line: str) -> bool:
    """
    Ignore lines that start with !Time: or are empty
    """
    return line.startswith("!Time: ") or line.startswith("!Running configuration")


def diff_cfg(old_cfg: str, new_cfg: str) -> str:
    """
    Compare two configurations and return the diff
    """
    old_cfg_line_by_line = [
        line for line in old_cfg.splitlines() if not ignore_config_diff_line(line)
    ]
    new_cfg_line_by_line = [
        line for line in old_cfg.splitlines() if not ignore_config_diff_line(line)
    ]

    diff = ""
    for line in difflib.unified_diff(
        old_cfg_line_by_line, new_cfg_line_by_line, lineterm=""
    ):
        line = line.strip()
        if len(line) > 0:
            diff += line + "\n"
    return diff


def run_preconfig_check(task: Task, snmp_config_commands: List[str]) -> Result:
    target_host = task.host
    platform = target_host.platform

    test_inventory_config = "testbed/nornir.yaml"

    target_cfg_file = "cfg/{}.cfg".format(target_host.name)
    with open(target_cfg_file, "r") as f:
        target_config_lines = f.readlines()
        # remove \n from each line
        target_config_lines = [line.rstrip("\n") for line in target_config_lines]

    # 1. generate sanitized config
    if platform == "ios":
        sanitize_config = sanitize_ios_config(target_config_lines)
    elif platform == "nxos_ssh":
        sanitize_config = sanitize_nxos_config(target_config_lines)
    else:
        raise ValueError(f"Unsupported platform: {platform}")

    # 2. get test device
    test_nr = (
        InitNornir(config_file=test_inventory_config)
        .filter(platform=platform)
        .filter(F(groups__contains="conftest"))
    )
    first_hostname = list(test_nr.inventory.hosts.keys())[0]
    test_device = test_nr.inventory.hosts[first_hostname]

    # 3. restore test device config
    test_device_init_config = "testbed/cfg/{}.cfg".format(test_device.name)

    # 4. use NAPALM to load init config and sanitize config
    test_con = test_device.get_connection(NAPALM_CONNECTION_NAME, test_nr.config)
    test_con.load_replace_candidate(filename=test_device_init_config)
    test_con.commit_config()
    test_con.load_merge_candidate(config="\n".join(sanitize_config))
    test_con.commit_config()

    pre_execute_config = test_con.get_config()["running"]

    # 5. test run the confi
    netmiko_test_con = test_device.get_connection(
        NETMIKO_CONNECTION_NAME, test_nr.config
    )
    config_result = netmiko_test_con.send_config_set(snmp_config_commands)

    if "Invalid" in config_result:
        return Result(
            host=task.host,
            result=f"Invalid configuration detected: {config_result}",
            changed=False,
            failed=True,
        )

    afrer_execute_config = test_con.get_config()["running"]

    config_dff = diff_cfg(pre_execute_config, afrer_execute_config)

    return Result(
        host=task.host,
        result=config_result,
        diff=config_dff,
        changed=True,
    )


def apply_netmiko_config(netmiko_connection, config_sets: List[str]):
    """
    Apply a list of configuration commands to the device using Netmiko.
    """
    try:
        result = netmiko_connection.send_config_set(config_sets)
        return result
    except Exception as e:
        logger.error(f"Failed to apply config: {e}")
        raise


# --- Main Task ---


def task(task: Task, dry_run: Optional[bool] = False) -> Result:
    snmp_vars = get_snmp_vars_from_host(task.host)

    netmiko_con = task.host.get_connection(NETMIKO_CONNECTION_NAME, task.nornir.config)
    if not netmiko_con:
        return Result(
            host=task.host,
            result="Failed to get Netmiko connection",
            changed=False,
            failed=True,  # Mark as failed if connection fails
        )

    platform = task.host.platform
    try:
        snmp_config_commands = generate_snmp_config(platform, snmp_vars)
    except (ValueError, FileNotFoundError) as e:
        return Result(
            host=task.host,
            result=f"Failed to generate SNMP config: {e}",
            changed=False,
            failed=True,
        )

    # --- Pre-Configuration Check ---

    precheck_result = run_preconfig_check(task, snmp_config_commands)

    if precheck_result.failed:
        # Return the detailed failure result from the pre-check
        return precheck_result

    # --- Apply to Target Device (if pre-check passed) ---
    if task.is_dry_run(dry_run):
        return Result(
            host=task.host,
            result="Dry run mode (pre-check successful), no changes applied to target.\n",
            diff=precheck_result.diff,
            changed=False,
        )

    # Apply the generated SNMP config commands to the actual target device

    try:
        # Use send_config_set for consistency with original code, though send_config might be better
        result_output = netmiko_con.send_config_set(snmp_config_commands)

        # Commit/Save based on platform
        if "iosxr" in platform:
            netmiko_con.commit()
        if platform in ["ios", "nxos_ssh"]:
            netmiko_con.save_config()

        return Result(
            host=task.host,
            result=result_output,
            diff=f"Pre-check Diff:\n{precheck_result.diff}\nTarget Diff:\n{result_output}",  # Combine diffs
            changed=True,  # Changes were applied to the target
        )
    except Exception as e:
        return Result(
            host=task.host,
            result=f"Failed applying config to target after successful pre-check: {e}",
            failed=True,
            changed=False,
        )
