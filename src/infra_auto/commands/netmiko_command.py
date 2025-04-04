from ..netmiko_command import netmiko_command_execute


class NetmikoCommand:
    def __init__(self, subparsers):
        # Netmiko Subparser
        netmiko_parser = subparsers.add_parser(
            "netmiko", help="Commands related to Netmiko operations"
        )
        netmiko_subparsers = netmiko_parser.add_subparsers(
            dest="command", required=True
        )

        # Netmiko: command execute
        netmiko_command_parser = netmiko_subparsers.add_parser(
            "execute", help="Execute a specific netmiko command module"
        )
        netmiko_command_parser.add_argument(
            "command",
            type=str,
            help="The command module name to execute (e.g., src.baseline_snmp.snmp_task)",
        )
        netmiko_command_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without making changes",
        )
        netmiko_command_parser.add_argument(
            "--device-list-file", type=str, help="Path to the device list file"
        )
        netmiko_command_parser.set_defaults(func=netmiko_command_execute)

    def netmiko_command_execute(self, args):
        netmiko_command_execute(args)
