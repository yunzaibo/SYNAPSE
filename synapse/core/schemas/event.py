"""Event — Market event of interest.

v2.0: recorded in Watchlist's why_now, no independent modeling.
v3.0: severity, confidence, decay, propagation state, contract link.
Lazy Upcast: v2.0 dicts create valid v3.0 Events with defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional

from synapse.core.schemas.base import BaseSchema
from synapse.analytics.tracking_models import OutcomeRecord


class EventType(str, Enum):
    # --- P2 types (unchanged) ---
    EARNINGS = "earnings"
    POLICY = "policy"
    PRODUCT_LAUNCH = "product_launch"
    MANAGEMENT_CHANGE = "management_change"
    SECTOR_ROTATION = "sector_rotation"
    MACRO_DATA = "macro_data"
    # --- v3.0 A-share types ---
    SENTIMENT = "sentiment"
    THEME = "theme"
    CAPITAL_FLOW = "capital_flow"
    CORPORATE_ACTION = "corporate_action"
    # --- v3.0 P3 enhancement types ---
    POLICY_CHANGE = "policy_change"
    MACRO_SHIFT = "macro_shift"


class ImpactLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class EventSourceType(str, Enum):
    """Origin of the event signal."""
    DATA_FEED = "data_feed"
    NEWS = "news"
    MANUAL = "manual"
    AI_DETECTED = "ai_detected"


class PropagationState(str, Enum):
    """Lifecycle state of event propagation in the graph."""
    DETECTED = "detected"
    PROPAGATING = "propagating"
    SETTLED = "settled"
    EXPIRED = "expired"


@dataclass
class Event(BaseSchema):
    """Market event of interest."""

    schema_version: str = "3.0"

    # --- Core (v2.0, unchanged) ---
    event_type: EventType = EventType.EARNINGS
    title: str = ""
    description: str = ""
    event_date: Optional[date] = None

    # --- Related (v2.0, unchanged) ---
    related_tickers: list[str] = field(default_factory=list)

    # --- Impact Assessment (v2.0, unchanged) ---
    impact_level: ImpactLevel = ImpactLevel.UNKNOWN

    # --- Outcome Tracking (v2.0, unchanged) ---
    outcome_tracking: list[OutcomeRecord] = field(default_factory=list)
    linked_review_ids: list[str] = field(default_factory=list)
    calibration_score: Optional[float] = None

    # --- v3.0 new fields ---
    severity: float = 0.5
    confidence: float = 0.5
    decay_rate: float = 0.1
    source: EventSourceType = EventSourceType.MANUAL
    propagation_state: PropagationState = PropagationState.DETECTED
    propagation_graph_id: Optional[str] = None
    contract_id: Optional[str] = None

    def __post_init__(self) -> None:
        self._validate_range("severity", self.severity, 0.0, 1.0)
        self._validate_range("confidence", self.confidence, 0.0, 1.0)

    @staticmethod
    def _validate_range(name: str, value: float, lo: float, hi: float) -> None:
        if not (lo <= value <= hi):
            raise ValueError(f"{name} must be in [{lo}, {hi}], got {value}")

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
            # v3.0 fields
            "severity": self.severity,
            "confidence": self.confidence,
            "decay_rate": self.decay_rate,
            "source": self.source.value,
            "propagation_state": self.propagation_state.value,
            "propagation_graph_id": self.propagation_graph_id,
            "contract_id": self.contract_id,
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
            # v3.0 fields — Lazy Upcast defaults for v2.0 dicts
            severity=float(data.get("severity", 0.5)),
            confidence=float(data.get("confidence", 0.5)),
            decay_rate=float(data.get("decay_rate", 0.1)),
            source=EventSourceType(data.get("source", "manual")),
            propagation_state=PropagationState(data.get("propagation_state", "detected")),
            propagation_graph_id=data.get("propagation_graph_id"),
            contract_id=data.get("contract_id"),
        )
