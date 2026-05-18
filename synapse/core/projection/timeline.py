"""Research Timeline — Append-only rendering of research history.

ADR-009: Append-only rendering.
- Never modify existing timeline entries
- Render from all canonical artifacts (Thesis, Decision, Review, Event)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from synapse.core.schemas.decision import Decision, DecisionType
from synapse.core.schemas.event import Event
from synapse.core.schemas.review import Review, ReviewOutcome
from synapse.core.schemas.thesis import Thesis


class TimelineEntryType(str, Enum):
    """Types of timeline entries."""
    THESIS_CREATED = "thesis_created"
    THESIS_REVISED = "thesis_revised"
    DECISION_RECORDED = "decision_recorded"
    REVIEW_COMPLETED = "review_completed"
    EVENT_OCCURRED = "event_occurred"


@dataclass
class TimelineEntry:
    """A single append-only timeline entry."""

    entry_type: TimelineEntryType
    timestamp: datetime
    object_id: str
    title: str
    summary: str
    linked_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entry_type": self.entry_type.value,
            "timestamp": self.timestamp.isoformat(),
            "object_id": self.object_id,
            "title": self.title,
            "summary": self.summary,
            "linked_ids": self.linked_ids,
        }


@dataclass
class TimelineView:
    """Complete research timeline view — append-only rendering."""

    entries: list[TimelineEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "count": len(self.entries),
        }

    @property
    def is_empty(self) -> bool:
        return len(self.entries) == 0


def _thesis_to_entries(thesis: Thesis) -> list[TimelineEntry]:
    """Convert a Thesis to timeline entries."""
    entries = []

    # Thesis creation
    entries.append(TimelineEntry(
        entry_type=TimelineEntryType.THESIS_CREATED,
        timestamp=thesis.created_at,
        object_id=thesis.id,
        title=thesis.title or thesis.slug,
        summary=thesis.thesis_statement or thesis.summary,
    ))

    # Thesis revision (if not first revision)
    if thesis.revision > 1 and thesis.previous_revision:
        entries.append(TimelineEntry(
            entry_type=TimelineEntryType.THESIS_REVISED,
            timestamp=thesis.updated_at,
            object_id=thesis.id,
            title=f"{thesis.title} (rev {thesis.revision})",
            summary=f"Thesis 修订至 rev {thesis.revision}",
            linked_ids=[thesis.parent_thesis_id] if thesis.parent_thesis_id else [],
        ))

    return entries


def _decision_to_entry(decision: Decision) -> TimelineEntry:
    """Convert a Decision to a timeline entry."""
    action = "买入" if decision.decision_type == DecisionType.BUY else "卖出"
    return TimelineEntry(
        entry_type=TimelineEntryType.DECISION_RECORDED,
        timestamp=decision.created_at,
        object_id=decision.id,
        title=f"{action} {decision.symbol or decision.ticker}",
        summary=decision.thesis,
        linked_ids=[
            tid for tid in [decision.linked_thesis_id, decision.linked_position_id] if tid
        ],
    )


def _review_to_entry(review: Review) -> TimelineEntry:
    """Convert a Review to a timeline entry."""
    outcome_map = {
        ReviewOutcome.THESIS_CONFIRMED: "Thesis 确认",
        ReviewOutcome.PARTIALLY_CONFIRMED: "Thesis 部分确认",
        ReviewOutcome.THESIS_INVALIDATED: "Thesis 无效",
    }
    outcome_text = outcome_map.get(review.review_outcome, "未知")

    return TimelineEntry(
        entry_type=TimelineEntryType.REVIEW_COMPLETED,
        timestamp=review.created_at,
        object_id=review.id,
        title=f"Review: {outcome_text}",
        summary=review.review_note or outcome_text,
        linked_ids=[
            tid for tid in [review.linked_decision_id, review.linked_thesis_id] if tid
        ],
    )


def _event_to_entry(event: Event) -> TimelineEntry:
    """Convert an Event to a timeline entry."""
    return TimelineEntry(
        entry_type=TimelineEntryType.EVENT_OCCURRED,
        timestamp=event.created_at,
        object_id=event.id,
        title=event.title,
        summary=event.description,
        linked_ids=[],
    )


def render_timeline(
    theses: Optional[list[Thesis]] = None,
    decisions: Optional[list[Decision]] = None,
    reviews: Optional[list[Review]] = None,
    events: Optional[list[Event]] = None,
) -> TimelineView:
    """Render an append-only research timeline from canonical artifacts.

    All existing entries are preserved — new entries are appended.
    This function is idempotent: calling it twice produces the same result
    for the same inputs.

    Args:
        theses: Thesis objects to include.
        decisions: Decision objects to include.
        reviews: Review objects to include.
        events: Event objects to include.

    Returns:
        TimelineView with entries sorted by timestamp ascending.
    """
    entries: list[TimelineEntry] = []

    # Convert all artifacts to timeline entries
    if theses:
        for thesis in theses:
            entries.extend(_thesis_to_entries(thesis))

    if decisions:
        for decision in decisions:
            entries.append(_decision_to_entry(decision))

    if reviews:
        for review in reviews:
            entries.append(_review_to_entry(review))

    if events:
        for event in events:
            entries.append(_event_to_entry(event))

    # Sort by timestamp (append-only order)
    entries.sort(key=lambda e: e.timestamp)

    return TimelineView(entries=entries)
