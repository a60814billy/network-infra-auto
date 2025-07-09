from nornir_utils.plugins.functions import print_result

from ..task_runners import NornirRunner


class SyncConfigFromDeviceCommand:
    def __init__(self, subparsers):
        # sync-config-from-device command
        sync_from_parser = subparsers.add_parser(
            "sync-config-from-device", help="Sync cfg from devices to git local"
        )
        sync_from_parser.set_defaults(func=self.sync_config_from_device)
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

    def sync_config_from_device(self, args):
        print("Syncing data from remote to local...")
        nr = NornirRunner(config_file=args.config_file).filter_hosts(
            args.device_list_file
        )
        nr.print_affect_hosts()
        print_result(nr.sync_from(dry_run=args.dry_run))
