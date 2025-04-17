from nornir_utils.plugins.functions import print_result

from ..infra_nornir import NornirRunner


class NornirCommand:
    def __init__(self, subparsers):
        # Nornir Subparser
        nornir_parser = subparsers.add_parser(
            "nornir", help="Commands related to Nornir operations"
        )
        nornir_subparsers = nornir_parser.add_subparsers(dest="command", required=True)

        # Nornir: sync-from command
        sync_from_parser = nornir_subparsers.add_parser(
            "sync-from", help="Sync cfg from devices to git local"
        )
        sync_from_parser.set_defaults(func=self.nornir_sync_from_devices)
        sync_from_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without making changes",
        )
        sync_from_parser.add_argument(
            "--device-list-file", type=str, help="Path to the device list file"
        )
        sync_from_parser.add_argument(
            "--config-file",
            "-c",
            type=str,
            help="Path to the config file",
            default="nornir.yaml",
        )

        # Nornir: sync-to command
        apply_to_parser = nornir_subparsers.add_parser(
            "apply", help="Apply and replace cfg from git local to devices"
        )
        apply_to_parser.set_defaults(func=self.nornir_apply_to_devices)
        apply_to_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without making changes",
        )
        apply_to_parser.add_argument(
            "--device-list-file", type=str, help="Path to the device list file"
        )
        apply_to_parser.add_argument(
            "--config-file",
            "-c",
            type=str,
            help="Path to the config file",
            default="nornir.yaml",
        )

    def nornir_sync_from_devices(self, args):
        print("Syncing data from remote to local...")
        nr = NornirRunner(config_file=args.config_file).filter_hosts(
            args.device_list_file
        )
        nr.print_affect_hosts()
        print_result(nr.sync_from(dry_run=args.dry_run))

    def nornir_apply_to_devices(self, args):
        print("Syncing data from local to remote...")
        nr = NornirRunner(config_file=args.config_file).filter_hosts(
            args.device_list_file
        )
        nr.print_affect_hosts()
        print_result(nr.apply_to(dry_run=args.dry_run))
