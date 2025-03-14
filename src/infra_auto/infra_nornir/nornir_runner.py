import os
from typing import Optional

from nornir import InitNornir
from nornir.core.filter import F

from .tasks import napalm_apply_config_to_devices, napalm_sync_config_from_devices


class NornirRunner:
    def __init__(self, nornir: InitNornir = None):
        if nornir:
            self.nornir = nornir
        else:
            self.nornir = InitNornir(config_file="nornir.yaml")

    def _device_list_exists(self):
        return os.path.exists(".change_device_list")

    def _read_device_list(self, device_list_file: str):
        with open(device_list_file, "r") as f:
            device_list = f.read().strip().split("\n")
        return [device for device in device_list if device]

    def filter_hosts(self, device_list_file: str):
        """
        Filter hosts based on .change_device_list if it exists
        """

        if not device_list_file:
            print("No device list file provided, syncing from all devices")
            return self

        if not os.path.exists(device_list_file):
            raise ValueError(f"Device list file {device_list_file} does not exist")

        device_list = self._read_device_list(device_list_file)
        print(f"Filtering to only sync from devices: {', '.join(device_list)}")
        filtered_nr = self.nornir.filter(F(name__in=device_list))

        return NornirRunner(nornir=filtered_nr)

    def print_affect_hosts(self):
        """
        Print all affected hosts
        """
        for host in self.nornir.inventory.hosts.values():
            print(host.name)

    def sync_from(self, dry_run: Optional[bool] = False):
        return self.nornir.run(task=napalm_sync_config_from_devices, dry_run=dry_run)

    def apply_to(self, dry_run: Optional[bool] = False):
        return self.nornir.run(task=napalm_apply_config_to_devices, dry_run=dry_run)
