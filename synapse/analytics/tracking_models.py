"""Tracking models for P2 analytics.

Shared dataclass models used by Signal decay tracking, Risk materialization
tracking, and Event outcome tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from synapse.core.temporal import CST


@dataclass
class DecaySnapshot:
    """Single decay measurement for a Signal."""

    signal_id: str
    decay_pct: float
    measured_at: datetime
    method: str = ""

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "decay_pct": self.decay_pct,
            "measured_at": self.measured_at.isoformat(),
            "method": self.method,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DecaySnapshot:
        return cls(
            signal_id=data["signal_id"],
            decay_pct=float(data["decay_pct"]),
            measured_at=datetime.fromisoformat(data["measured_at"]),
            method=data.get("method", ""),
        )


@dataclass
class MaterializationSnapshot:
    """Single materialization check for a Risk."""

    risk_id: str
    materialized: bool
    detected_at: datetime
    source_review_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "risk_id": self.risk_id,
            "materialized": self.materialized,
            "detected_at": self.detected_at.isoformat(),
            "source_review_id": self.source_review_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MaterializationSnapshot:
        return cls(
            risk_id=data["risk_id"],
            materialized=bool(data["materialized"]),
            detected_at=datetime.fromisoformat(data["detected_at"]),
            source_review_id=data.get("source_review_id"),
        )


@dataclass
class OutcomeRecord:
    """Outcome tracking entry for an Event."""

    event_id: str
    review_id: str
    impact_assessment: str = ""
    calibrated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "review_id": self.review_id,
            "impact_assessment": self.impact_assessment,
            "calibrated_at": self.calibrated_at.isoformat() if self.calibrated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> OutcomeRecord:
        calibrated = data.get("calibrated_at")
        return cls(
            event_id=data["event_id"],
            review_id=data["review_id"],
            impact_assessment=data.get("impact_assessment", ""),
            calibrated_at=datetime.fromisoformat(calibrated) if calibrated else None,
        )
