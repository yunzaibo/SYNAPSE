"""Thesis append-only revision management.

Thesis Evolution rules from 01_Research_Object_Schema.md:
- Revisions are append-only: rev-001.md, rev-002.md, ...
- meta.yaml always points to the latest revision
- Never overwrite a revision — always create a new one
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml


class ThesisDir:
    """Manages a thesis directory on disk."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @property
    def meta_path(self) -> Path:
        return self.path / "meta.yaml"

    def revision_path(self, rev_num: int) -> Path:
        return self.path / f"rev-{rev_num:03d}.md"

    def list_revisions(self) -> list[int]:
        """List existing revision numbers, sorted ascending."""
        nums = []
        for p in self.path.glob("rev-*.md"):
            try:
                num = int(p.stem.split("-")[1])
                nums.append(num)
            except (IndexError, ValueError):
                continue
        return sorted(nums)

    def next_revision(self) -> int:
        """Return the next revision number."""
        existing = self.list_revisions()
        return (max(existing) + 1) if existing else 1

    def read_meta(self) -> dict:
        """Read meta.yaml content."""
        if not self.meta_path.exists():
            return {}
        with open(self.meta_path) as f:
            return yaml.safe_load(f) or {}

    def write_meta(self, data: dict) -> None:
        """Write meta.yaml content."""
        with open(self.meta_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def _find_thesis_dir(base: Path, thesis_id: str) -> Path | None:
    """Find thesis directory matching the given ID pattern."""
    if not base.is_dir():
        return None
    for d in base.iterdir():
        if d.is_dir() and d.name.startswith(f"{thesis_id}_"):
            return d
    return None


def create_revision(
    thesis_id: str,
    content: str,
    *,
    workspace: str | Path = ".",
) -> Path:
    """Create a new append-only revision for a thesis.

    Args:
        thesis_id: Thesis ID like 'ths_7f8c91'.
        content: Revision content in markdown.
        workspace: Workspace root path (default: current directory).

    Returns:
        Path to the newly created revision file.

    Raises:
        FileNotFoundError: If thesis directory does not exist.
    """
    base = Path(workspace) / "thesis"
    thesis_dir = _find_thesis_dir(base, thesis_id)
    if thesis_dir is None:
        raise FileNotFoundError(f"Thesis directory not found for {thesis_id}")

    td = ThesisDir(thesis_dir)
    rev_num = td.next_revision()
    rev_path = td.revision_path(rev_num)

    # Append-only: never overwrite
    rev_path.write_text(content, encoding="utf-8")

    # Update meta.yaml to point to latest revision
    meta = td.read_meta()
    meta["revision"] = rev_num
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    td.write_meta(meta)

    return rev_path


def get_current_revision(thesis_id: str, *, workspace: str | Path = ".") -> int:
    """Get the current (latest) revision number.

    Args:
        thesis_id: Thesis ID like 'ths_7f8c91'.
        workspace: Workspace root path.

    Returns:
        Current revision number (0 if no revisions exist).
    """
    base = Path(workspace) / "thesis"
    thesis_dir = _find_thesis_dir(base, thesis_id)
    if thesis_dir is None:
        return 0

    td = ThesisDir(thesis_dir)
    existing = td.list_revisions()
    return max(existing) if existing else 0


def list_revisions(thesis_id: str, *, workspace: str | Path = ".") -> list[int]:
    """List all revision numbers for a thesis.

    Args:
        thesis_id: Thesis ID like 'ths_7f8c91'.
        workspace: Workspace root path.

    Returns:
        Sorted list of revision numbers.
    """
    base = Path(workspace) / "thesis"
    thesis_dir = _find_thesis_dir(base, thesis_id)
    if thesis_dir is None:
        return []

    return ThesisDir(thesis_dir).list_revisions()
