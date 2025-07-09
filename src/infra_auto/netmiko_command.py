import argparse
import importlib
import os
import sys

from nornir_utils.plugins.functions import print_result

from infra_auto.task_runners import NornirRunner


def netmiko_command_execute(args: argparse.Namespace) -> None:
    command = args.command

    # dynamic import of the command module
    importlib.import_module(command)
    # get filter function in the command module
    filter_func = getattr(sys.modules[command], "filter_hosts", None)
    task_func = getattr(sys.modules[command], "task", None)

    # get module path
    module_path = os.path.dirname(sys.modules[command].__file__)

    group_vars_path = os.path.join(module_path, "vars/groups.yaml")
    host_vars_path = os.path.join(module_path, "vars/hosts.yaml")

    nr_runner = NornirRunner()
    # load group vars and host vars
    nr_runner.load_group_vars(command, group_vars_path)
    nr_runner.load_host_vars(command, host_vars_path)

    if args.device_list_file:
        nr_runner.filter_hosts(args.device_list_file)
    nr_runner.nornir = nr_runner.nornir.filter(filter_func=filter_func)
    nr_runner.print_affect_hosts()

    result = nr_runner.nornir.run(task=task_func, dry_run=args.dry_run)
    print_result(result)
