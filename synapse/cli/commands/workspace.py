"""CLI command: synapse workspace list/switch

List available workspaces or switch between them.
"""

from __future__ import annotations

import argparse

from synapse.core.workspace_v2 import WorkspaceManager


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the workspace subcommand."""
    parser = subparsers.add_parser(
        "workspace",
        help="Workspace management",
        description="List and switch between SYNAPSE workspaces.",
    )
    workspace_sub = parser.add_subparsers(dest="workspace_command", help="Workspace commands")

    # list subcommand
    list_parser = workspace_sub.add_parser(
        "list",
        help="List available workspaces",
        description="Show all workspaces found in the workspaces root directory.",
    )
    list_parser.set_defaults(func=run_list)

    # switch subcommand
    switch_parser = workspace_sub.add_parser(
        "switch",
        help="Switch active workspace",
        description="Set the active workspace by name.",
    )
    switch_parser.add_argument(
        "name",
        help="Workspace name to switch to",
    )
    switch_parser.set_defaults(func=run_switch)


def run_list(args: argparse.Namespace) -> int:
    """Execute the workspace list command."""
    manager = WorkspaceManager()
    workspaces = manager.list_workspaces()

    if not workspaces:
        print("No workspaces found.")
        print(f"Root: {manager.workspaces_root}")
        return 0

    print(f"Workspaces ({manager.workspaces_root}):")
    for ws in workspaces:
        print(f"  - {ws['name']}: {ws['path']}")

    return 0


def run_switch(args: argparse.Namespace) -> int:
    """Execute the workspace switch command."""
    manager = WorkspaceManager()

    try:
        ws_path = manager.switch_workspace(args.name)
        print(f"Switched to workspace: {args.name}")
        print(f"  Path: {ws_path}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
