"""Event — Market event of interest.

P1: recorded in Watchlist's why_now, no independent modeling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional

from synapse.core.schemas.base import BaseSchema
from synapse.analytics.tracking_models import OutcomeRecord


class EventType(str, Enum):
    EARNINGS = "earnings"
    POLICY = "policy"
    PRODUCT_LAUNCH = "product_launch"
    MANAGEMENT_CHANGE = "management_change"
    SECTOR_ROTATION = "sector_rotation"
    MACRO_DATA = "macro_data"


class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


@dataclass
class Event(BaseSchema):
    """Market event of interest."""

    schema_version: str = "2.0"

    # --- Core ---
    event_type: EventType = EventType.EARNINGS
    title: str = ""
    description: str = ""
    event_date: Optional[date] = None

    # --- Related ---
    related_tickers: list[str] = field(default_factory=list)

    # --- Impact Assessment ---
    impact_level: ImpactLevel = ImpactLevel.UNKNOWN

    # --- Outcome Tracking (P2) ---
    outcome_tracking: list[OutcomeRecord] = field(default_factory=list)
    linked_review_ids: list[str] = field(default_factory=list)
    calibration_score: Optional[float] = None

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "event_type": self.event_type.value,
            "title": self.title,
            "description": self.description,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "related_tickers": self.related_tickers,
            "impact_level": self.impact_level.value,
            "outcome_tracking": [o.to_dict() for o in self.outcome_tracking],
            "linked_review_ids": self.linked_review_ids,
            "calibration_score": self.calibration_score,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Event:
        base = cls.base_from_dict(data)
        return cls(
            **base,
            event_type=EventType(data.get("event_type", "earnings")),
            title=data.get("title", ""),
            description=data.get("description", ""),
            event_date=date.fromisoformat(data["event_date"]) if data.get("event_date") else None,
            related_tickers=data.get("related_tickers", []),
            impact_level=ImpactLevel(data.get("impact_level", "unknown")),
            outcome_tracking=[OutcomeRecord.from_dict(o) for o in data.get("outcome_tracking", [])],
            linked_review_ids=data.get("linked_review_ids", []),
            calibration_score=float(data["calibration_score"]) if data.get("calibration_score") is not None else None,
        )
