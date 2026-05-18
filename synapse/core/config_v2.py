"""Global config (config.toml) and workspace config (synapse.yaml) loading.

GlobalConfig loads from TOML (Python 3.11+ built-in tomllib).
WorkspaceManager handles workspace-level YAML config.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SidecarConfig:
    path: str = ".synapse-sidecar"
    heartbeat_interval: int = 30


@dataclass
class LoggingConfig:
    level: str = "INFO"


@dataclass
class WorkspaceDefaultConfig:
    default_path: str = "~/SYNAPSE-Workspaces"


@dataclass
class GlobalConfig:
    """Global configuration loaded from config.toml."""

    sidecar: SidecarConfig = field(default_factory=SidecarConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    workspace: WorkspaceDefaultConfig = field(default_factory=WorkspaceDefaultConfig)

    @classmethod
    def load(cls, path: str | Path) -> GlobalConfig:
        """Load config from a TOML file and return a GlobalConfig instance."""
        with open(path, "rb") as f:
            raw = tomllib.load(f)

        sidecar_raw = raw.get("sidecar", {})
        logging_raw = raw.get("logging", {})
        workspace_raw = raw.get("workspace", {})

        return cls(
            sidecar=SidecarConfig(
                path=sidecar_raw.get("path", ".synapse-sidecar"),
                heartbeat_interval=sidecar_raw.get("heartbeat_interval", 30),
            ),
            logging=LoggingConfig(
                level=logging_raw.get("level", "INFO"),
            ),
            workspace=WorkspaceDefaultConfig(
                default_path=workspace_raw.get("default_path", "~/SYNAPSE-Workspaces"),
            ),
        )


def load_workspace_config(path: str | Path) -> dict:
    """Load workspace config (synapse.yaml) and return as dict."""
    import yaml

    with open(path) as f:
        return yaml.safe_load(f)
