import argparse
import os

from nornir import InitNornir
from nornir.core.filter import F
from nornir.core.task import Result, Task
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="nornir.yaml")


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
            # write running to startup
            changed = True
        else:
            changed = False

        return Result(host=task.host, changed=changed, diff=diff)

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Sync running config to device")
    parser.add_argument("--dry-run", action="store_true", help="Print diff only")
    args = parser.parse_args()
    dry_run = args.dry_run

    if not os.path.exists('.change_device_list'):
        print('No device change list found')
        change_device_set = nr.filter(name='empty-set')
    else:
        with open('.change_device_list', 'r') as f:
            device_list = f.read().splitlines()
        print('Devices to sync: ', device_list)
        change_device_set = nr.filter(F(name__in=device_list))

    result = change_device_set.run(task=sync_cfg_to_device, dry_run=dry_run)
    print_result(result)


if __name__ == '__main__':
    main()
