"""SYNAPSE CLI entry point — register all subcommands.

Thin wrapper over core modules. All business logic lives in synapse.core.
"""

from __future__ import annotations

import argparse
import sys

from synapse.cli.commands import init, research, decision, review, workspace, analytics, event


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="synapse",
        description="SYNAPSE — AI-native Quant Research OS",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Register subcommands
    init.register(subparsers)
    research.register(subparsers)
    decision.register(subparsers)
    review.register(subparsers)
    workspace.register(subparsers)
    analytics.register(subparsers)
    event.register(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns 0 on success, non-zero on error."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        return args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
