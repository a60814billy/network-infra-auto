import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from infra_auto.commands import NornirCommand, CiCommand, NetmikoCommand


def main() -> None:
    parser = argparse.ArgumentParser(prog="iac_auto")
    subparsers = parser.add_subparsers(dest="category", required=True)

    NornirCommand(subparsers)
    CiCommand(subparsers)
    NetmikoCommand(subparsers)

    args = parser.parse_args()

    # Handle cases where category or command might be missing (though subparsers should handle this)
    if not hasattr(args, "category") or not hasattr(args, "command"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
