import tempfile
from pathlib import Path

import pytest
import yaml

from synapse.core.config_v2 import GlobalConfig, WorkspaceDefaultConfig
from synapse.core.workspace_v2 import WORKSPACE_DIRS, WorkspaceManager


@pytest.fixture
def workspace_path(tmp_path):
    return tmp_path / "test-workspace"


@pytest.fixture
def manager():
    return WorkspaceManager()


@pytest.fixture
def manager_with_config(tmp_path):
    config = GlobalConfig(
        workspace=WorkspaceDefaultConfig(default_path=str(tmp_path / "workspaces"))
    )
    return WorkspaceManager(global_config=config)


class TestWorkspaceManagerInit:
    def test_init_workspace_creates_all_dirs(self, workspace_path, manager):
        created = manager.init_workspace(workspace_path)
        assert len(created) == len(WORKSPACE_DIRS)
        for d in WORKSPACE_DIRS:
            assert (workspace_path / d).is_dir()

    def test_init_workspace_creates_synapse_yaml(self, workspace_path, manager):
        manager.init_workspace(workspace_path)
        config_path = workspace_path / "synapse.yaml"
        assert config_path.exists()

    def test_init_workspace_yaml_has_required_keys(self, workspace_path, manager):
        manager.init_workspace(workspace_path)
        config = manager.load_workspace_config(workspace_path)
        assert config["schema_version"] == "1.0"
        assert config["workspace_name"] == "test-workspace"
        assert "research_preferences" in config
        assert "signal_preferences" in config
        assert "ai_behavior" in config

    def test_init_workspace_idempotent(self, workspace_path, manager):
        manager.init_workspace(workspace_path)
        created = manager.init_workspace(workspace_path)
        assert len(created) == len(WORKSPACE_DIRS)


class TestWorkspaceManagerLoadConfig:
    def test_load_workspace_config(self, workspace_path, manager):
        manager.init_workspace(workspace_path)
        config = manager.load_workspace_config(workspace_path)
        assert isinstance(config, dict)
        assert config["schema_version"] == "1.0"

    def test_load_workspace_config_nonexistent(self, tmp_path, manager):
        with pytest.raises(FileNotFoundError):
            manager.load_workspace_config(tmp_path / "nonexistent")


class TestWorkspaceManagerList:
    def test_list_empty(self, tmp_path, manager_with_config):
        results = manager_with_config.list_workspaces()
        assert results == []

    def test_list_finds_workspaces(self, manager_with_config):
        root = Path(manager_with_config.workspaces_root)
        root.mkdir(parents=True, exist_ok=True)
        ws1 = root / "ws-alpha"
        ws2 = root / "ws-beta"
        manager_with_config.init_workspace(ws1)
        manager_with_config.init_workspace(ws2)
        results = manager_with_config.list_workspaces()
        names = [ws["name"] for ws in results]
        assert "ws-alpha" in names
        assert "ws-beta" in names

    def test_list_ignores_dirs_without_config(self, manager_with_config):
        root = Path(manager_with_config.workspaces_root)
        root.mkdir(parents=True, exist_ok=True)
        (root / "no-config-dir").mkdir()
        results = manager_with_config.list_workspaces()
        assert results == []


class TestWorkspaceManagerSwitch:
    def test_switch_workspace(self, manager_with_config):
        root = Path(manager_with_config.workspaces_root)
        root.mkdir(parents=True, exist_ok=True)
        ws = root / "my-research"
        manager_with_config.init_workspace(ws)
        result = manager_with_config.switch_workspace("my-research")
        assert result == ws
        assert manager_with_config._global_config.workspace.default_path == str(ws)

    def test_switch_nonexistent_raises(self, manager_with_config):
        with pytest.raises(ValueError, match="not found"):
            manager_with_config.switch_workspace("does-not-exist")


class TestWorkspaceDirs:
    def test_standard_dirs_count(self):
        assert len(WORKSPACE_DIRS) == 10

    def test_standard_dirs_include_required(self):
        required = {"thesis", "decisions", "watchlists", "positions",
                     "events", "reports", "artifacts", "attachments",
                     "snapshots", ".index"}
        assert set(WORKSPACE_DIRS) == required
