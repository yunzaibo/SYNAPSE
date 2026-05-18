import tempfile
from pathlib import Path

import pytest

from synapse.core.config_v2 import GlobalConfig, load_workspace_config


SAMPLE_TOML = """\
[sidecar]
path = ".my-sidecar"
heartbeat_interval = 60

[logging]
level = "DEBUG"

[workspace]
default_path = "/tmp/test-workspaces"
"""

MINIMAL_TOML = """\
[sidecar]
"""


@pytest.fixture
def toml_file(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(SAMPLE_TOML)
    return config_path


@pytest.fixture
def minimal_toml_file(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(MINIMAL_TOML)
    return config_path


class TestGlobalConfig:
    def test_load_from_toml(self, toml_file):
        config = GlobalConfig.load(toml_file)
        assert config.sidecar.path == ".my-sidecar"
        assert config.sidecar.heartbeat_interval == 60
        assert config.logging.level == "DEBUG"
        assert config.workspace.default_path == "/tmp/test-workspaces"

    def test_load_minimal_toml_uses_defaults(self, minimal_toml_file):
        config = GlobalConfig.load(minimal_toml_file)
        assert config.sidecar.path == ".synapse-sidecar"
        assert config.sidecar.heartbeat_interval == 30
        assert config.logging.level == "INFO"
        assert config.workspace.default_path == "~/SYNAPSE-Workspaces"

    def test_load_empty_toml_uses_defaults(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text("")
        config = GlobalConfig.load(config_path)
        assert config.sidecar.path == ".synapse-sidecar"
        assert config.logging.level == "INFO"

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            GlobalConfig.load("/nonexistent/config.toml")


class TestLoadWorkspaceConfig:
    def test_load_workspace_yaml(self, tmp_path):
        yaml_content = (
            'schema_version: "1.0"\n'
            "workspace_name: test-ws\n"
            "research_preferences:\n"
            "  focus: sector_analysis\n"
        )
        config_path = tmp_path / "synapse.yaml"
        config_path.write_text(yaml_content)
        config = load_workspace_config(config_path)
        assert config["schema_version"] == "1.0"
        assert config["workspace_name"] == "test-ws"
        assert config["research_preferences"]["focus"] == "sector_analysis"

    def test_load_nonexistent_yaml(self):
        with pytest.raises(FileNotFoundError):
            load_workspace_config("/nonexistent/synapse.yaml")
