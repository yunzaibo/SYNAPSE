"""Review — Decision post-mortem evaluation.

Optional but encouraged: evaluates thesis validity, not P&L.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from synapse.core.schemas.base import BaseSchema


class ReviewOutcome(str, Enum):
    THESIS_CONFIRMED = "thesis_confirmed"
    PARTIALLY_CONFIRMED = "partially_confirmed"
    THESIS_INVALIDATED = "thesis_invalidated"


@dataclass
class SignalEvaluation:
    """Evaluation of a signal's accuracy."""

    linked_signal_id: str
    was_accurate: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "linked_signal_id": self.linked_signal_id,
            "was_accurate": self.was_accurate,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SignalEvaluation:
        return cls(
            linked_signal_id=data["linked_signal_id"],
            was_accurate=data.get("was_accurate", False),
            note=data.get("note", ""),
        )


@dataclass
class RiskEvaluation:
    """Evaluation of whether a risk materialized."""

    description: str = ""
    materialized: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "materialized": self.materialized,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RiskEvaluation:
        return cls(
            description=data.get("description", ""),
            materialized=data.get("materialized", False),
            note=data.get("note", ""),
        )


@dataclass
class Review(BaseSchema):
    """Decision post-mortem — evaluates thesis validity."""

    # --- Link ---
    linked_decision_id: Optional[str] = None
    linked_thesis_id: Optional[str] = None

    # --- Outcome ---
    review_outcome: ReviewOutcome = ReviewOutcome.THESIS_CONFIRMED

    # --- Note ---
    review_note: str = ""

    # --- Signal Evaluation ---
    signal_evaluations: list[SignalEvaluation] = field(default_factory=list)

    # --- Risk Evaluation ---
    risk_evaluations: list[RiskEvaluation] = field(default_factory=list)

    # --- Event Reference (IMPL-007) ---
    event_id: Optional[str] = None
    event_trigger_type: Optional[str] = None  # "direct" | "propagated" | "manual"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "linked_decision_id": self.linked_decision_id,
            "linked_thesis_id": self.linked_thesis_id,
            "review_outcome": self.review_outcome.value,
            "review_note": self.review_note,
            "signal_evaluations": [se.to_dict() for se in self.signal_evaluations],
            "risk_evaluations": [re.to_dict() for re in self.risk_evaluations],
            # Event reference fields
            "event_id": self.event_id,
            "event_trigger_type": self.event_trigger_type,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Review:
        base = cls.base_from_dict(data)
        return cls(
            **base,
            linked_decision_id=data.get("linked_decision_id"),
            linked_thesis_id=data.get("linked_thesis_id"),
            review_outcome=ReviewOutcome(data.get("review_outcome", "thesis_confirmed")),
            review_note=data.get("review_note", ""),
            signal_evaluations=[SignalEvaluation.from_dict(se) for se in data.get("signal_evaluations", [])],
            risk_evaluations=[RiskEvaluation.from_dict(re) for re in data.get("risk_evaluations", [])],
            # Event reference fields — Lazy Upcast defaults
            event_id=data.get("event_id"),
            event_trigger_type=data.get("event_trigger_type"),
        )
