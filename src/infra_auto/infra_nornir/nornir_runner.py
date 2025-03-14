import os
from nornir import InitNornir
from nornir.core.filter import F

class NornirRunner:
    def __init__(self, nornir: InitNornir = None):
        if nornir:
            self.nornir = nornir
        else:
            self.nornir = InitNornir(config_file="nornir.yaml")

    def _device_list_exists(self):
        return os.path.exists(".change_device_list")
    
    def _read_device_list(self):
        if not self._device_list_exists():
            return []
        
        with open(".change_device_list", "r") as f:
            device_list = f.read().strip().split("\n")
        return [device for device in device_list if device]

    def filter_hosts(self):
        """
        Filter hosts based on .change_device_list if it exists
        """
        if not self._device_list_exists():
            print("No device filter applied, syncing from all devices")
            return self
        
        device_list = self._read_device_list()
        print(f"Filtering to only sync from devices: {', '.join(device_list)}")
        filtered_nr = self.nornir.filter(F(name__in=device_list))

        return NornirRunner(nornir=filtered_nr)
    
    def print_affect_hosts(self):
        """
        Print all affected hosts
        """
        for host in self.nornir.inventory.hosts.values():
            print(host.name)

    def sync_from(self):
        pass

    def sync_to(self, dry_run: bool = False):
        pass
