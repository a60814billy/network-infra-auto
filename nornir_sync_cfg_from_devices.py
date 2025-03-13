import difflib
import argparse

import napalm
from nornir import InitNornir
from nornir.core.task import MultiResult, Result, Task
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="nornir.yaml")


def sync_cfg_from_device(task: Task, dry_run: bool = False) -> Result:
    local_cfg_path = f'cfg/{task.host.name}.cfg'

    # if file exists, read it
    try:
        with open(local_cfg_path, 'r') as f:
            local_cfg = f.read()
    except FileNotFoundError:
        local_cfg = ""
        pass

    conn = task.host.get_connection('napalm', task.nornir.config)
    try:
        conn.open()
        # if platform is nxos, use get checkpoint
        if task.host.platform == 'nxos_ssh':
            cfg = conn._get_checkpoint_file()
        else:
            cfg = conn.get_config()['running']
    finally:
        conn.close()
    
    
    diff = ""

    local_cfg_for_diff = [line for line in local_cfg.splitlines() if not line.startswith('!Time: ')]
    remote_cfg_for_diff = [line for line in cfg.splitlines() if not line.startswith('!Time: ')]

    for l in difflib.unified_diff(local_cfg_for_diff, remote_cfg_for_diff, lineterm=''):
        diff += l + "\n"
    diff = diff.strip()
    if diff:
        changed = True
    else:
        changed = False

    if dry_run:
        return Result(host=task.host, changed=changed, diff=diff)

    if diff:
        with open(local_cfg_path, 'w') as f:
            f.write(cfg)
    return Result(host=task.host, changed=changed)


def main():
    parser = argparse.ArgumentParser(description="Sync running config from device")
    parser.add_argument("--dry-run", action="store_true", help="Print diff only")
    args = parser.parse_args()
    dry_run = args.dry_run
    result = nr.run(task=sync_cfg_from_device, dry_run=dry_run)
    print_result(result)

if __name__ == '__main__':
    main()
