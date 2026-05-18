"""Workspace management for SYNAPSE research workspaces.

WorkspaceManager handles workspace initialization, config loading, listing,
and switching. Each workspace contains standard directories for research objects.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from synapse.core.config_v2 import GlobalConfig, load_workspace_config

# Canonical workspace directories per Research Object Schema
WORKSPACE_DIRS = [
    "thesis",
    "decisions",
    "watchlists",
    "positions",
    "events",
    "reports",
    "artifacts",
    "attachments",
    "snapshots",
    ".index",
]

WORKSPACE_CONFIG_FILE = "synapse.yaml"


class WorkspaceManager:
    """Manages SYNAPSE research workspaces."""

    def __init__(self, global_config: GlobalConfig | None = None):
        self._global_config = global_config

    @property
    def workspaces_root(self) -> Path:
        """Return the root directory for all workspaces."""
        if self._global_config:
            return Path(self._global_config.workspace.default_path).expanduser()
        return Path("~/SYNAPSE-Workspaces").expanduser()

    def init_workspace(self, path: str | Path) -> list[Path]:
        """Create standard workspace directories. Returns list of created dirs."""
        base = Path(path)
        created = []
        for d in WORKSPACE_DIRS:
            dir_path = base / d
            dir_path.mkdir(parents=True, exist_ok=True)
            created.append(dir_path)
        # Create default synapse.yaml if not present
        config_path = base / WORKSPACE_CONFIG_FILE
        if not config_path.exists():
            default_config = {
                "schema_version": "1.0",
                "workspace_name": base.name,
                "research_preferences": {},
                "signal_preferences": {},
                "ai_behavior": {},
            }
            with open(config_path, "w") as f:
                yaml.dump(default_config, f, default_flow_style=False)
        return created

    def load_workspace_config(self, workspace_path: str | Path) -> dict:
        """Read synapse.yaml from a workspace and return as dict."""
        config_path = Path(workspace_path) / WORKSPACE_CONFIG_FILE
        return load_workspace_config(config_path)

    def list_workspaces(self) -> list[dict]:
        """Scan workspaces root for dirs containing synapse.yaml.

        Returns list of dicts with 'name', 'path', and 'config' keys.
        """
        root = self.workspaces_root
        if not root.is_dir():
            return []

        results = []
        for entry in sorted(root.iterdir()):
            if entry.is_dir():
                config_path = entry / WORKSPACE_CONFIG_FILE
                if config_path.exists():
                    config = load_workspace_config(config_path)
                    results.append({
                        "name": config.get("workspace_name", entry.name),
                        "path": str(entry),
                        "config": config,
                    })
        return results

    def switch_workspace(self, workspace_name: str) -> Path:
        """Set the active workspace by name. Updates global config default_path.

        Returns the path of the activated workspace.
        Raises ValueError if workspace not found.
        """
        workspaces = self.list_workspaces()
        for ws in workspaces:
            if ws["name"] == workspace_name:
                ws_path = Path(ws["path"])
                if self._global_config:
                    self._global_config.workspace.default_path = str(ws_path)
                return ws_path
        available = [ws["name"] for ws in workspaces]
        raise ValueError(
            f"Workspace '{workspace_name}' not found. "
            f"Available: {available}"
        )
