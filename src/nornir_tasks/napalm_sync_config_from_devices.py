import difflib
from typing import Optional

from nornir.core.task import Result, Task
from nornir_napalm.plugins.connections import CONNECTION_NAME


def diff_cfg(old_cfg: str, new_cfg: str) -> str:
    """
    Compare two configurations and return the diff
    """
    old_cfg_line_by_line = [
        line for line in old_cfg.splitlines() if not line.startswith("!Time: ")
    ]
    new_cfg_line_by_line = [
        line for line in new_cfg.splitlines() if not line.startswith("!Time: ")
    ]

    diff = ""
    for line in difflib.unified_diff(
        old_cfg_line_by_line, new_cfg_line_by_line, lineterm=""
    ):
        line = line.strip()
        if len(line) > 0:
            diff += line + "\n"
    return diff


def napalm_sync_config_from_devices(
    task: Task, dry_run: Optional[bool] = False
) -> Result:
    changed = False
    diff = ""
    result = ""

    local_cfg_path = f"cfg/{task.host.name}.cfg"

    # if file exists, read it
    try:
        with open(local_cfg_path, "r") as f:
            local_cfg = f.read()
    except FileNotFoundError:
        local_cfg = ""

    conn = task.host.get_connection(CONNECTION_NAME, task.nornir.config)
    try:
        conn.open()
        # if platform is nxos, use get checkpoint
        if task.host.platform == "nxos_ssh":
            cfg = conn._get_checkpoint_file()
        else:
            cfg = conn.get_config()["running"]
    finally:
        conn.close()

    diff = diff_cfg(local_cfg, cfg)

    if diff:
        changed = True
        result = f"Config has changed for {task.host.name}"
    else:
        changed = False
        result = f"Config has not changed for {task.host.name}"

    if task.is_dry_run(dry_run):
        print("Dry run: No changes will be made")
        return Result(host=task.host, changed=changed, diff=diff, result=result)

    if diff:
        with open(local_cfg_path, "w") as f:
            f.write(cfg)

    return Result(host=task.host, changed=changed, diff=diff, result=result)
