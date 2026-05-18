import yaml
from pathlib import Path

def load_config(path: str | Path) -> dict:
    """Load YAML config file and return as dict."""
    with open(path) as f:
        return yaml.safe_load(f)

def validate_config(config: dict, required_keys: list[str] | None = None) -> list[str]:
    """Validate config has required keys. Returns list of missing keys."""
    if required_keys is None:
        required_keys = ["project_name", "domain"]
    return [k for k in required_keys if k not in config]
