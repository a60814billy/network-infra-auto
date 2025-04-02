import os
import sys
import importlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import argparse

from nornir_utils.plugins.functions import print_result

from infra_auto.ci_utils.tasks import (
    detect_cfg_changes,
    report_changes_to_mr_comment,
    trigger_post_deploy_pipeline,
)
from infra_auto.infra_nornir import NornirRunner


def nornir_sync_from_devices(args: argparse.Namespace) -> None:
    print("Syncing data from remote to local...")
    nr = NornirRunner().filter_hosts(args.device_list_file)
    nr.print_affect_hosts()
    print_result(nr.sync_from(dry_run=args.dry_run))


def nornir_apply_to_devices(args: argparse.Namespace) -> None:
    print("Syncing data from local to remote...")
    nr = NornirRunner().filter_hosts(args.device_list_file)
    nr.print_affect_hosts()
    print_result(nr.apply_to(dry_run=args.dry_run))


def ci_detect_changes(args: argparse.Namespace) -> None:
    detect_cfg_changes()


def ci_report_diff_to_mr_comment(args: argparse.Namespace) -> None:
    report_changes_to_mr_comment(args.report_file)


def ci_trigger_sync_from_pipeline(args: argparse.Namespace) -> None:
    trigger_post_deploy_pipeline(args.device_list_file)


def netmiko_command_execute(args: argparse.Namespace) -> None:
    command = args.command
    # dynamic import of the command module
    importlib.import_module(command)
    # get filter function in the command module
    filter_func = getattr(sys.modules[command], "filter_hosts", None)
    task_func = getattr(sys.modules[command], "task", None)

    nr_runner = NornirRunner()
    if args.device_list_file:
        nr_runner.filter_hosts(args.device_list_file)
    nr_runner.nornir = nr_runner.nornir.filter(filter_func=filter_func)
    nr_runner.print_affect_hosts()

    nr_runner.nornir.run(task=task_func, dry_run=args.dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(prog="iac_auto")
    subparsers = parser.add_subparsers(dest="category", required=True)

    # Nornir Subparser
    nornir_parser = subparsers.add_parser(
        "nornir", help="Commands related to Nornir operations"
    )
    nornir_subparsers = nornir_parser.add_subparsers(dest="command", required=True)

    # Nornir: sync-from command
    sync_from_parser = nornir_subparsers.add_parser(
        "sync-from", help="Sync cfg from devices to git local"
    )
    sync_from_parser.set_defaults(func=nornir_sync_from_devices)
    sync_from_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    sync_from_parser.add_argument(
        "--device-list-file", type=str, help="Path to the device list file"
    )

    # Nornir: sync-to command
    apply_to_parser = nornir_subparsers.add_parser(
        "apply", help="Apply and replace cfg from git local to devices"
    )
    apply_to_parser.set_defaults(func=nornir_apply_to_devices)
    apply_to_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    apply_to_parser.add_argument(
        "--device-list-file", type=str, help="Path to the device list file"
    )

    # CI Subparser
    ci_parser = subparsers.add_parser(
        "ci",
        help="Commands related to CI operations (only for GitLab CI use, not for manual use)",
    )
    ci_subparsers = ci_parser.add_subparsers(dest="command", required=True)

    # CI: detect-changes command
    ci_detect_change_parser = ci_subparsers.add_parser(
        "detect-changes", help="Detect changes in the repository"
    )
    ci_detect_change_parser.set_defaults(func=ci_detect_changes)

    # CI: report command
    ci_report_to_mr_comment_parser = ci_subparsers.add_parser(
        "report-diff-to-mr", help="Generate a CI report"
    )
    ci_report_to_mr_comment_parser.set_defaults(func=ci_report_diff_to_mr_comment)
    ci_report_to_mr_comment_parser.add_argument(
        "--report-file", type=str, help="Path to the report file"
    )

    # CI: trigger sync command
    ci_trigger_parser = ci_subparsers.add_parser(
        "trigger-sync-from-pipeline", help="Trigger CI operations"
    )
    ci_trigger_parser.set_defaults(func=ci_trigger_sync_from_pipeline)
    ci_trigger_parser.add_argument(
        "--device-list-file", type=str, help="Path to the device list file"
    )

    # Netmiko Subparser
    netmiko_parser = subparsers.add_parser(
        "netmiko", help="Commands related to Netmiko operations"
    )
    netmiko_subparsers = netmiko_parser.add_subparsers(dest="command", required=True)

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

    args = parser.parse_args()

    # Handle cases where category or command might be missing (though subparsers should handle this)
    if not hasattr(args, "category") or not hasattr(args, "command"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
