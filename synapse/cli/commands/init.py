"""CLI command: synapse init [path]

Create a new SYNAPSE workspace with standard directories and config.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from synapse.core.workspace_v2 import WorkspaceManager


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the init subcommand."""
    parser = subparsers.add_parser(
        "init",
        help="Initialize a new SYNAPSE workspace",
        description="Create a new SYNAPSE workspace with standard directories and config.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Workspace directory path (default: current directory)",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Execute the init command."""
    workspace_path = Path(args.path).resolve()
    manager = WorkspaceManager()

    print(f"Initializing workspace at: {workspace_path}")
    created = manager.init_workspace(workspace_path)
    print(f"Created {len(created)} directories")

    config_path = workspace_path / "synapse.yaml"
    print(f"Config: {config_path}")

    return 0
