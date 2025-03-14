from typing import Optional

from nornir.core.task import Task, Result
from nornir_napalm.plugins.connections import CONNECTION_NAME

def napalm_apply_config_to_devices(task: Task, dry_run: Optional[bool] = False) -> Result:
    diff = ""
    changed = False
    result = ""

    local_cfg_path = f'cfg/{task.host.name}.cfg'

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
