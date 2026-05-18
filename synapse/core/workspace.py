from pathlib import Path

STANDARD_DIRS = [
    "data/sample",
    "factors",
    "experiments",
    "backtests",
    "reports",
    "artifacts",
    "configs",
]

def init_workspace(path: str | Path) -> list[Path]:
    """Create standard project directories. Returns list of created dirs."""
    base = Path(path)
    created = []
    for d in STANDARD_DIRS:
        dir_path = base / d
        dir_path.mkdir(parents=True, exist_ok=True)
        created.append(dir_path)
    return created

def check_workspace(path: str | Path) -> dict[str, bool]:
    """Check which standard directories exist. Returns dict of dir -> exists."""
    base = Path(path)
    return {d: (base / d).is_dir() for d in STANDARD_DIRS}
