import difflib
import argparse
import os

import napalm
from nornir import InitNornir
from nornir.core.task import MultiResult, Result, Task
from nornir.core.filter import F
from nornir_utils.plugins.functions import print_result

nr = InitNornir(config_file="nornir.yaml")

# Filter hosts based on .change_device_list if it exists
def filter_hosts():
    if os.path.exists(".change_device_list"):
        with open(".change_device_list", "r") as f:
            device_list = f.read().strip().split("\n")
        
        # Filter out empty lines
        device_list = [device for device in device_list if device]
        
        if device_list:
            print(f"Filtering to only sync from devices: {', '.join(device_list)}")
            return nr.filter(F(name__in=device_list))
    
    print("No device filter applied, syncing from all devices")
    return nr


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
    
    # Get filtered inventory based on .change_device_list
    filtered_nr = filter_hosts()
    
    result = filtered_nr.run(task=sync_cfg_from_device, dry_run=dry_run)
    print_result(result)

if __name__ == '__main__':
    main()
