from typing import Optional

from nornir.core.task import Result, Task
from nornir_napalm.plugins.connections import CONNECTION_NAME


def check_config_hostname(
    task: Task, config_path: str, dry_run: Optional[bool] = None
) -> Result:
    """
    Check if the hostname in the configuration file matches the Nornir host name.
    """
    with open(config_path, "r") as f:
        config = f.read()

    configured_hostname = ""
    if task.host.platform in ["ios", "iosxr", "nxos_ssh"]:
        config = [line.strip() for line in config.splitlines() if line.strip()]
        for line in config:
            if line.startswith("hostname "):
                configured_hostname = line.split(" ")[1]
                break
    elif task.host.platform in ["hpe_comware"]:
        config = [line.strip() for line in config.splitlines() if line.strip()]
        for line in config:
            if line.startswith("sysname "):
                configured_hostname = line.split(" ")[1]
                break
    else:
        raise ValueError(f"Unsupported platform: {task.host.platform}")

    if configured_hostname == "" or configured_hostname != task.host.name:
        raise ValueError(
            f"Configured hostname '{configured_hostname}' does not match Nornir hostname '{task.host.name}'"
        )

    return Result(
        host=task.host,
        changed=True,
        result=f"hostname check passed for {task.host.name}",
    )


def napalm_apply_config_to_devices(
    task: Task, dry_run: Optional[bool] = None
) -> Result:
    diff = ""
    changed = False
    result = ""

    local_cfg_path = f"cfg/{task.host.name}.cfg"

    task.run(task=check_config_hostname, config_path=local_cfg_path)

    conn = task.host.get_connection(CONNECTION_NAME, task.nornir.config)

    try:
        conn.open()
        conn.load_replace_candidate(filename=local_cfg_path)
        diff = conn.compare_config()

        if diff:
            changed = True
            result = f"Config changes detected for {task.host.name}"
        else:
            changed = False
            result = f"No config changes detected for {task.host.name}"

        if task.is_dry_run(dry_run):
            return Result(host=task.host, changed=changed, diff=diff, result=result)

        if diff:
            conn.commit_config()

        return Result(host=task.host, changed=changed, diff=diff, result=result)

    finally:
        conn.close()
