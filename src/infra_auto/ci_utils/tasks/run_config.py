import os
from typing import List, Optional
from pathlib import Path

from nornir.core.task import Result, Task
from nornir_utils.plugins.functions import print_result
from nornir_napalm.plugins.connections import CONNECTION_NAME

from infra_auto.infra_nornir import NornirRunner


def napalm_apply_specific_config(task: Task, configs: str) -> Result:
    """
    Apply a specific config file to a device using NAPALM

    Args:
        task: Nornir task
        config_name: Name of the config file to apply
    """
    result = ""
    diff = ""
    changed = False

    conn = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    conn.open()
    conn.load_merge_candidate(config="\n".join(configs))
    diff = conn.compare_config()

    if diff:
        changed = True
        result = f"Config changes detected for {task.host.name}"
    else:
        changed = False
        result = f"No config changes detected for {task.host.name}"

    if diff:
        conn.commit_config()

    return Result(host=task.host, changed=changed, diff=diff, result=result)


def run_specific_configs(
    configs: List[str], device_list_file: Optional[str] = None
) -> None:
    """
    Run specific config files using NAPALM

    Args:
        configs: List of config files to run
        device_list_file: Optional path to device list file
    """
    if not configs:
        print("No config files specified. Nothing to do.")
        return

    print(f"Running specific configs: {', '.join(configs)}")

    # Initialize the Nornir runner
    nr = NornirRunner()

    # Filter hosts if device list file is provided
    if device_list_file:
        nr = nr.filter_hosts(device_list_file)

    nr.print_affect_hosts()

    result = nr.nornir.run(task=napalm_apply_specific_config, configs=configs)
    print_result(result)

    print("Configuration application complete")
