import difflib
import os
import re
from typing import Dict, List

from nornir import InitNornir
from nornir.core import Nornir
from nornir.core.task import Result, Task
from nornir_utils.plugins.functions import print_result

from ..infra_nornir.tasks.napalm_sync_config_from_devices import (
    napalm_sync_config_from_devices,
)


class ChangeHostnameTaskRunner:
    _mapping: dict[str, str]
    _nornir: Nornir

    def __init__(self, hosts: List[Dict[str, str]]):
        # build old/new hostname mapping
        self._mapping = {}

        for host in hosts:
            self._mapping[host["host"]] = host["new"]

        self._old_hosts = list(self._mapping.keys())

        # setup nornir instance before file change
        self._nornir = InitNornir(config_file='nornir.yaml')

    def check_host(self, host: str):
        # 1. check host in hosts.yaml
        if self._nornir.inventory.hosts.get(host) is None:
            return False

        # 2. check cfg exists
        if not os.path.exists(f"./cfg/{host}.cfg"):
            return False

        return True

    def _change_hosts_yaml(self, dry_run: bool = False):
        with open("./inventory/hosts.yaml", "r") as hosts_file:
            hosts_content = hosts_file.read()

        old_content = hosts_content

        for old_host, new_host in self._mapping.items():
            # use regex to replace host
            # the pattern is ^${host}:$
            hosts_content = re.sub(
                f"^{re.escape(old_host)}:$",
                f"{new_host}:",
                hosts_content,
                flags=re.MULTILINE,
            )

        if dry_run:
            d = difflib.Differ()
            diff = d.compare(old_content.splitlines(keepends=True), hosts_content.splitlines(keepends=True))
            print('changes of hosts.yaml:')
            print("".join(diff))
            return

        with open("./inventory/hosts.yaml", "w") as hosts_file:
            hosts_file.write(hosts_content)

    def _change_cfg_filename(self, dry_run: bool = False):
        for old_host, new_host in self._mapping.items():
            if dry_run:
                print(f"rename {old_host}.cfg to {new_host}.cfg")
            else:
                os.rename(f"./cfg/{old_host}.cfg", f"./cfg/{new_host}.cfg")

    def _run_change_hostname_task(self):
        mapping = self._mapping

        def change_hostname(task: Task, dry_run: bool = False) -> Result:
            new_hostname = mapping[task.host.name]
            if task.host.platform in ["ios", "nxos_ssh", "iosxr"]:
                if not task.is_dry_run(dry_run):
                    conn = task.host.get_connection("netmiko", task.nornir.config)
                    result = conn.send_config_set(
                        [
                            f"hostname {new_hostname}",
                        ]
                    )
            return Result(host=task.host, result=result, changed=True)

        result = self._nornir.filter(
            filter_func=lambda host: host.name in self._old_hosts
        ).run(task=change_hostname)
        print_result(result)

    def _run_sync_from_task(self):
        nr = InitNornir(config_file="nornir.yaml")
        new_hosts = self._mapping.values()
        result = nr.filter(filter_func=lambda h: h.name in new_hosts).run(
            task=napalm_sync_config_from_devices
        )
        print_result(result)

    def run(self, dry_run: bool = False):
        all_ok = True
        for host in self._old_hosts:
            if not self.check_host(host):
                print(f"check failed: {host}")
                all_ok = False

        if all_ok:
            # do task
            # 1. change hosts.yaml
            self._change_hosts_yaml(dry_run)
            # 2. change cfg/ filename
            self._change_cfg_filename(dry_run)

            if not dry_run:
                # 3. change all config,
                self._run_change_hostname_task()
                # 4. use new config to run sync from change devices
                self._run_sync_from_task()
