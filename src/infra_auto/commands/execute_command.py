
from infra_auto.task_runners import ExecuteTaskModuleRunner


class ExecuteCommand:
    def __init__(self, subparsers):
        # Execute command parser
        execute_parser = subparsers.add_parser(
            "execute", help="Execute a specific netmiko command module"
        )
        execute_parser.add_argument(
            "command",
            type=str,
            help="The command module name to execute (e.g., src.baseline_snmp.snmp_task)",
        )
        execute_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without making changes",
        )
        execute_parser.add_argument(
            "--device-list-file", type=str, help="Path to the device list file"
        )
        execute_parser.set_defaults(func=self.execute)

    def execute(self, args):
        ExecuteTaskModuleRunner(args.command, args.device_list_file).run(dry_run=args.dry_run)
        pass