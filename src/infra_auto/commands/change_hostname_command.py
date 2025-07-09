import yaml

from infra_auto.task_runners import ChangeHostnameTaskRunner


class ChangeHostnameCommand:
    def __init__(self, subparsers):
        # Change Hostname Subparser
        change_hostname_parser = subparsers.add_parser(
            "change-hostname", help="Change hostname of network devices"
        )
        change_hostname_parser.set_defaults(func=self.change_hostname)
        change_hostname_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without making changes",
        )
        change_hostname_parser.add_argument(
            "--task-file",
            "-t",
            type=str,
            help="Path to the task file containing hostname mappings",
            default="task.yaml",
        )

    def change_hostname(self, args):
        print("Starting hostname change process...")

        # Load task configuration
        try:
            with open(args.task_file, "r") as task_file:
                task = yaml.safe_load(task_file)
        except FileNotFoundError:
            print(f"Error: Task file '{args.task_file}' not found")
            return
        except yaml.YAMLError as e:
            print(f"Error parsing task file: {e}")
            return

        # Validate task structure
        if task.get("task") != "change_hostname":
            print("Error: Task file must contain 'task: change_hostname'")
            return

        if "hosts" not in task:
            print("Error: Task file must contain 'hosts' section")
            return

        # Create and run the task runner
        runner = ChangeHostnameTaskRunner(task["hosts"])

        if args.dry_run:
            print("Running in dry-run mode...")

        runner.run(dry_run=args.dry_run)

        if args.dry_run:
            print("Dry-run completed. No changes were made.")
        else:
            print("Hostname change process completed.")
