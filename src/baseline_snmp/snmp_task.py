import os
import re
import ipaddress
from typing import Optional, List
import logging

from jinja2 import Template
from nornir import InitNornir
from nornir.core.task import Task, Result

from .sanitize_config import sanitize_ios_config

from nornir_netmiko import CONNECTION_NAME as NETMIKO_CONNECTION_NAME
from nornir_napalm.plugins.connections import CONNECTION_NAME as NAPALM_CONNECTION_NAME

# Configure logging for Nornir initialization within the task (use cautiously)
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

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


def run_preconfig_check(task: Task, snmp_config_commands: List[str]) -> Result:
    """
    Runs pre-configuration checks on a test device.

    1. Initializes Nornir for the test inventory.
    2. Finds a test device matching the target's platform.
    3. Sanitizes the target's full config.
    4. Applies the sanitized config to the test device.
    5. Applies the specific SNMP commands to the test device.
    6. Returns the result, including diff/output.
    """
    target_host = task.host
    platform = target_host.platform
    test_inventory_config = "test_nornir.yaml"  # Assumption

    target_cfg_file = "cfg/{}.cfg".format(target_host.name)
    with open(target_cfg_file, "r") as f:
        target_config_lines = f.readlines()

    # 1. generate sanitized config
    sanitize_config = sanitize_ios_config(target_config_lines)

    # 2. get test device
    test_nr = InitNornir(config_file=test_inventory_config)
    test_nr = test_nr.filter(platform=platform)
    first_hostname = list(test_nr.inventory.hosts.keys())[0]
    test_device = test_nr.inventory.hosts[first_hostname]

    # 3. restore test device config
    test_device_init_config = "test_cfg/{}.cfg".format(test_device.name)

    # 4. use NAPALM to load init config and sanitize config
    test_con = test_device.get_connection(NAPALM_CONNECTION_NAME, test_nr.config)
    test_con.load_replace_candidate(filename=test_device_init_config)
    test_con.load_merge_candidate(config="\n".join(sanitize_config))
    test_con.commit_config()

    netmiko_test_con = test_device.get_connection(
        NETMIKO_CONNECTION_NAME, test_nr.config
    )
    netmiko_test_con.send_config_set(snmp_config_commands)
    test_con.commit_config()


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
    logger.info(f"Starting pre-config check for {task.host.name}")

    precheck_result = run_preconfig_check(task, snmp_config_commands)

    if precheck_result.failed:
        logger.warning(f"Pre-config check failed for {task.host.name}. Aborting task.")
        # Return the detailed failure result from the pre-check
        return precheck_result
    else:
        logger.info(f"Pre-config check successful for {task.host.name}.")
        # Optionally include pre-check diff in the final result?
        # final_diff = f"{precheck_result.diff}\n--- Target Device {task.host.name} Apply Output ---\n"

    # --- Apply to Target Device (if pre-check passed) ---
    if task.is_dry_run(dry_run):
        # In dry-run, show the commands that *would* be applied after successful pre-check
        return Result(
            host=task.host,
            result="Dry run mode (pre-check successful), no changes applied to target.",
            diff="\n".join(
                snmp_config_commands
            ),  # Show SNMP commands intended for target
            changed=False,
        )

    # Apply the generated SNMP config commands to the actual target device
    logger.info(f"Applying SNMP config to target device {task.host.name}")
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
        logger.error(
            f"Failed to apply config to target device {task.host.name} after pre-check: {e}"
        )
        return Result(
            host=task.host,
            result=f"Failed applying config to target after successful pre-check: {e}",
            failed=True,
            changed=False,  # Or potentially True if some commands went through? Risky.
        )
    # Note: The function should have returned by now, either from pre-check failure,
    # dry-run, successful application, or application failure.
    # The lines below were part of the old structure and are removed.
