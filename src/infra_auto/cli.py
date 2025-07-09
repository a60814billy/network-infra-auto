import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from infra_auto.commands import NornirCommand, CiCommand, NetmikoCommand, ChangeHostnameCommand


def main() -> None:
    parser = argparse.ArgumentParser(prog="iac_auto")
    subparsers = parser.add_subparsers(dest="category", required=True)

    NornirCommand(subparsers)
    CiCommand(subparsers)
    NetmikoCommand(subparsers)
    ChangeHostnameCommand(subparsers)

    args = parser.parse_args()

    # Handle cases where category might be missing (though subparsers should handle this)
    if not hasattr(args, "category"):
        parser.print_help()
        sys.exit(1)
    
    # Some commands like change-hostname don't have subcommands, so they won't have a 'command' attribute
    # Only check for 'command' if it's expected (for commands with subcommands)
    if args.category in ["nornir", "ci", "netmiko"] and not hasattr(args, "command"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
