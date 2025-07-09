from nornir_utils.plugins.functions import print_result

from ..infra_nornir import NornirRunner


class ApplyCfgToDeviceCommand:
    def __init__(self, subparsers):
        # apply-cfg-to-device command
        apply_to_parser = subparsers.add_parser(
            "apply-cfg-to-device",
            help="Apply and replace cfg from git local to devices",
        )
        apply_to_parser.set_defaults(func=self.apply_cfg_to_device)
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

    def apply_cfg_to_device(self, args):
        print("Syncing data from local to remote...")
        nr = NornirRunner(config_file=args.config_file).filter_hosts(
            args.device_list_file
        )
        nr.print_affect_hosts()
        print_result(nr.apply_to(dry_run=args.dry_run))
