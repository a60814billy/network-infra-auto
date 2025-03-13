import difflib
import argparse

import napalm
from nornir import InitNornir
from nornir.core.task import MultiResult, Result, Task
from nornir_utils.plugins.functions import print_result

nr = InitNornir()


def sync_cfg_to_device(task: Task, dry_run: bool = False) -> Result:
    local_cfg_path = f'cfg/{task.host.name}.cfg'

    conn = task.host.get_connection('napalm', task.nornir.config)

    try:
        conn.open()
        conn.load_replace_candidate(filename=local_cfg_path)
        diff = conn.compare_config()

        if dry_run:
            if diff:
                changed = True
            else:
                changed = False
            return Result(host=task.host, changed=changed, diff=diff)

        if conn.compare_config():
            conn.commit_config()
            changed = True
        else:
            changed = False

        return Result(host=task.host, changed=changed)

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Sync running config to device")
    parser.add_argument("--dry-run", action="store_true", help="Print diff only")
    args = parser.parse_args()
    dry_run = args.dry_run
    result = nr.run(task=sync_cfg_to_device, dry_run=dry_run)
    print_result(result)

if __name__ == '__main__':
    main()
