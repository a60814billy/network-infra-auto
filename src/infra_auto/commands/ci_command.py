import os
import sys

from ..ci_utils.tasks import (
    detect_cfg_changes,
    report_changes_to_mr_comment,
    run_specific_configs,
    trigger_post_deploy_pipeline,
)


class CiCommand:
    def __init__(self, subparsers):
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
        ci_detect_change_parser.set_defaults(func=self.ci_detect_changes)

        # CI: report command
        ci_report_to_mr_comment_parser = ci_subparsers.add_parser(
            "report-diff-to-mr", help="Generate a CI report"
        )
        ci_report_to_mr_comment_parser.set_defaults(
            func=self.ci_report_diff_to_mr_comment
        )
        ci_report_to_mr_comment_parser.add_argument(
            "--report-file", type=str, help="Path to the report file"
        )

        # CI: trigger sync command
        ci_trigger_parser = ci_subparsers.add_parser(
            "trigger-sync-from-pipeline", help="Trigger CI operations"
        )
        ci_trigger_parser.set_defaults(func=self.ci_trigger_sync_from_pipeline)
        ci_trigger_parser.add_argument(
            "--device-list-file", type=str, help="Path to the device list file"
        )

        # CI: run_config command
        ci_run_config_parser = ci_subparsers.add_parser(
            "run_config", help="Run specific configurations using NAPALM"
        )
        ci_run_config_parser.set_defaults(func=self.ci_run_config)
        ci_run_config_parser.add_argument(
            "--configs", type=str, help="Comma-separated list of configs to run"
        )
        ci_run_config_parser.add_argument(
            "--device-list-file", type=str, help="Path to the device list file"
        )

    def ci_detect_changes(self, args):
        detect_cfg_changes()

    def ci_report_diff_to_mr_comment(self, args):
        report_changes_to_mr_comment(args.report_file)

    def ci_trigger_sync_from_pipeline(self, args):
        trigger_post_deploy_pipeline(args.device_list_file)

    def ci_run_config(self, args):
        # First check if configs are provided via command line
        configs = []
        if args.configs:
            configs = args.configs.split(",")
        # If not, check for CI_RUN_CONFIGS environment variable
        elif os.environ.get("CI_RUN_CONFIGS"):
            configs = os.environ.get("CI_RUN_CONFIGS").split(",")

        if not configs:
            print(
                "No configs specified. Please provide configs using --configs or CI_RUN_CONFIGS environment variable."
            )
            sys.exit(1)

        run_specific_configs(configs, args.device_list_file)
