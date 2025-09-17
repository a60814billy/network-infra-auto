import difflib
from typing import List

from nornir import InitNornir
from nornir.core.task import Result, Task
from nornir.core.filter import F
from nornir_napalm.plugins.connections import CONNECTION_NAME as NAPALM_CONNECTION_NAME
from nornir_netmiko import CONNECTION_NAME as NETMIKO_CONNECTION_NAME

from config_utils import sanitize_config


def ignore_config_diff_line(line: str) -> bool:
    """
    Ignore lines that start with !Time: or are empty
    """
    return (
        line.startswith("!Time: ")  # IOS-XE
        or line.startswith("!Running configuration")  # NXOS
        or line.startswith("!! Last configuration")  # IOS-XR
    )


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


def run_preconfig_check(task: Task, extra_commands: List[str]) -> Result:
    print("Running pre-configuration check...")
    target_host = task.host
    platform = target_host.platform

    test_inventory_config = "testbed/nornir.yaml"

    target_cfg_file = "cfg/{}.cfg".format(target_host.name)
    with open(target_cfg_file, "r") as f:
        target_config_lines = f.readlines()
        # remove \n from each line
        target_config_lines = [line.rstrip("\n") for line in target_config_lines]

    # 1. generate sanitized config
    sanitized_config = sanitize_config(platform, target_config_lines)

    # 2. get test device
    test_nr = (
        InitNornir(config_file=test_inventory_config)
        .filter(platform=platform)
        .filter(F(groups__contains="conftest"))
    )
    first_hostname = list(test_nr.inventory.hosts.keys())[0]
    test_device = test_nr.inventory.hosts[first_hostname]

    print("Test config on {}".format(test_device.name))

    # 3. restore test device config
    test_device_init_config = "testbed/cfg/{}.cfg".format(test_device.name)

    # 4. use NAPALM to load init config and sanitize config
    test_con = test_device.get_connection(NAPALM_CONNECTION_NAME, test_nr.config)
    test_con.load_replace_candidate(filename=test_device_init_config)
    test_con.commit_config()

    test_con.load_merge_candidate(config="\n".join(sanitized_config))
    test_con.commit_config()

    netmiko_test_con = test_device.get_connection(
        NETMIKO_CONNECTION_NAME, test_nr.config
    )

    # 5. use netmiko to send config line by line to the device
    # this is to ensure that each line is applied successfully
    for line in sanitized_config:
        print("Sending command: {}".format(line))
        output = netmiko_test_con.send_config_set([line])
        if "Invalid" in output:
            return Result(
                host=task.host,
                result=f"Invalid configuration detected: {output}\n at line: {line}",
                changed=False,
                failed=True,
            )

    pre_execute_config = test_con.get_config()["running"]

    config_result = ""
    # 6. test run the extra config commands
    netmiko_test_con = test_device.get_connection(
        NETMIKO_CONNECTION_NAME, test_nr.config
    )
    for line in extra_commands:
        print("Sending command: {}".format(line))
        output = netmiko_test_con.send_config_set([line])
        if "Invalid" in output:
            return Result(
                host=task.host,
                result=f"Invalid configuration detected: {output}\n at line: {line}",
                changed=False,
                failed=True,
            )
        config_result += output + "\n"

    if platform == "iosxr":
        netmiko_test_con.commit()

    after_execute_config = test_con.get_config()["running"]

    config_diff = diff_cfg(pre_execute_config, after_execute_config)

    return Result(
        host=task.host,
        result=config_result,
        diff=config_diff,
        changed=True,
    )
