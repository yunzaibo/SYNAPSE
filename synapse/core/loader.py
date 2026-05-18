"""Object Loader — YAML load/save for research objects.

Auto-detects object type from content, provides round-trip serialization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml

from synapse.core.schemas.base import BaseSchema
from synapse.core.schemas.watchlist import WatchlistEntry
from synapse.core.schemas.thesis import Thesis
from synapse.core.schemas.decision import Decision
from synapse.core.schemas.review import Review
from synapse.core.schemas.position import Position
from synapse.core.schemas.signal import Signal
from synapse.core.schemas.risk import Risk
from synapse.core.schemas.event import Event
from synapse.core.schemas.topic import ResearchTopic


# Object type registry: maps slug → class
_OBJECT_TYPES: dict[str, type[BaseSchema]] = {
    "wl": WatchlistEntry,
    "ths": Thesis,
    "dec": Decision,
    "rev": Review,
    "pos": Position,
    "sig": Signal,
    "rsk": Risk,
    "evt": Event,
    "top": ResearchTopic,
}


def _detect_type(data: dict) -> type[BaseSchema] | None:
    """Detect object type from YAML content.

    Uses id prefix to determine type (e.g. 'ths_xxx' → Thesis).
    """
    obj_id = data.get("id", "")
    if not obj_id:
        return None
    prefix = obj_id.split("_")[0] if "_" in obj_id else ""
    return _OBJECT_TYPES.get(prefix)


def load_object(path: str | Path) -> BaseSchema:
    """Load a research object from YAML file.

    Auto-detects type from the id prefix in the file content.

    Args:
        path: Path to the YAML file.

    Returns:
        Deserialized research object.

    Raises:
        ValueError: If file content cannot be parsed or type is unknown.
        FileNotFoundError: If file does not exist.
    """
    path = Path(path)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML dict, got {type(data).__name__}")

    obj_type = _detect_type(data)
    if obj_type is None:
        raise ValueError(f"Cannot detect object type from id: {data.get('id', '<missing>')}")

    return obj_type.from_dict(data)


def save_object(obj: BaseSchema, path: str | Path) -> Path:
    """Save a research object to YAML file.

    Args:
        obj: Research object to save.
        path: Target file path.

    Returns:
        The path that was written to.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = obj.to_dict()
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return path


def register_object_type(prefix: str, cls: type[BaseSchema]) -> None:
    """Register a custom object type for auto-detection."""
    _OBJECT_TYPES[prefix] = cls
