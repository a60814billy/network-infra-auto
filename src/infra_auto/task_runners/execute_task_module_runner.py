import importlib
import os
import sys

from nornir_utils.plugins.functions import print_result


class ExecuteTaskModuleRunner:
    def __init__(self, task_module_name: str, device_list_file: str = None):
        self.device_list_file = device_list_file
        self.module_name = task_module_name
        # dynamic import of the command module
        importlib.import_module(task_module_name)

        # get filter function in the command module
        self.filter_func = getattr(sys.modules[task_module_name], "filter_hosts", None)
        self.task_func = getattr(sys.modules[task_module_name], "task", None)

        # get module path
        module_path = os.path.dirname(sys.modules[task_module_name].__file__)

        self.group_vars_path = os.path.join(module_path, "vars/groups.yaml")
        self.host_vars_path = os.path.join(module_path, "vars/hosts.yaml")

    def run(self, dry_run: bool = False):
        task_runner = importlib.import_module('infra_auto.task_runners')
        nr_runner = task_runner.NornirRunner()
        # load group vars and host vars
        nr_runner.load_group_vars(self.module_name, self.group_vars_path)
        nr_runner.load_host_vars(self.module_name, self.host_vars_path)

        if self.device_list_file:
            nr_runner.filter_hosts(self.device_list_file)
        nr_runner.nornir = nr_runner.nornir.filter(filter_func=self.filter_func)
        nr_runner.print_affect_hosts()

        result = nr_runner.nornir.run(task=self.task_func, dry_run=dry_run)
        print_result(result)