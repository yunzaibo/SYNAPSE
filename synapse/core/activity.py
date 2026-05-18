"""Activity Taxonomy — Immutable operation log for research objects.

ADR-010: activity.jsonl is an immutable, append-only log.
Defines what to log (research activities), what not to log (runtime noise),
and the forbidden types that must never appear in the log.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional


CST = timezone(timedelta(hours=8))


class ActivityType(str, Enum):
    """Allowed activity types for research operations.

    Research Activities (must log):
        thesis.created, thesis.revised
        decision.recorded
        review.completed
        watchlist.generated
        position.opened, position.closed

    Runtime Activities (optional):
        projection.rebuilt, workspace.indexed
    """

    # Research Activities
    THESIS_CREATED = "thesis.created"
    THESIS_REVISED = "thesis.revised"
    DECISION_RECORDED = "decision.recorded"
    REVIEW_COMPLETED = "review.completed"
    WATCHLIST_GENERATED = "watchlist.generated"
    POSITION_OPENED = "position.opened"
    POSITION_CLOSED = "position.closed"

    # Runtime Activities
    PROJECTION_REBUILT = "projection.rebuilt"
    WORKSPACE_INDEXED = "workspace.indexed"


# Forbidden types that must never appear in activity.jsonl
FORBIDDEN_TYPES: set[str] = {
    "token.stream",
    "llm.raw.reasoning",
    "debug.spam",
    "file.watcher.event",
}


@dataclass(frozen=True)
class ActivityEntry:
    """Single immutable activity log entry."""

    ts: str
    type: str
    obj_id: str
    actor: str
    summary: str

    def to_jsonl(self) -> str:
        """Serialize to JSONL format."""
        return json.dumps(
            {
                "ts": self.ts,
                "type": self.type,
                "obj_id": self.obj_id,
                "actor": self.actor,
                "summary": self.summary,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_dict(cls, data: dict) -> ActivityEntry:
        """Deserialize from dict."""
        return cls(
            ts=data["ts"],
            type=data["type"],
            obj_id=data["obj_id"],
            actor=data["actor"],
            summary=data["summary"],
        )


class ActivityLog:
    """Immutable, append-only activity log for research operations.

    Writes to activity.jsonl in JSONL format. Supports append and read.
    """

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)

    def append(
        self,
        activity_type: str,
        obj_id: str,
        actor: str,
        summary: str,
        ts: Optional[str] = None,
    ) -> ActivityEntry:
        """Append an activity entry to the log.

        Args:
            activity_type: Activity type string (must be a valid ActivityType value).
            obj_id: ID of the affected object.
            actor: Who performed the action ('human' or 'ai').
            summary: Human-readable description of the action.
            ts: ISO 8601 timestamp. Defaults to now in Asia/Shanghai.

        Returns:
            The created ActivityEntry.

        Raises:
            ValueError: If activity_type is forbidden.
        """
        if activity_type in FORBIDDEN_TYPES:
            raise ValueError(
                f"Forbidden activity type: {activity_type!r}. "
                f"Forbidden types: {FORBIDDEN_TYPES}"
            )

        if ts is None:
            ts = datetime.now(CST).isoformat()

        entry = ActivityEntry(
            ts=ts,
            type=activity_type,
            obj_id=obj_id,
            actor=actor,
            summary=summary,
        )

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(entry.to_jsonl() + "\n")

        return entry

    def read_all(self) -> list[ActivityEntry]:
        """Read all entries from the log file."""
        if not self.log_path.exists():
            return []

        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    entries.append(ActivityEntry.from_dict(data))
        return entries

    def is_empty(self) -> bool:
        """Check if the log file is empty or doesn't exist."""
        if not self.log_path.exists():
            return True
        return self.log_path.stat().st_size == 0

    def count(self) -> int:
        """Count the number of entries in the log."""
        return len(self.read_all())
