"""Risk — Independent risk hypothesis.

P1: recorded in Decision's key_risk, no independent tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from synapse.core.schemas.base import BaseSchema
from synapse.analytics.tracking_models import MaterializationSnapshot


class RiskType(str, Enum):
    VALUATION = "valuation"
    LIQUIDITY = "liquidity"
    REGULATORY = "regulatory"
    EVENT_DECAY = "event_decay"
    MACRO = "macro"
    SECTOR = "sector"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Risk(BaseSchema):
    """Independent risk hypothesis."""

    schema_version: str = "2.0"

    # --- Core ---
    risk_type: RiskType = RiskType.VALUATION
    description: str = ""
    severity: Severity = Severity.MEDIUM

    # --- Related ---
    related_tickers: list[str] = field(default_factory=list)
    linked_decision_id: Optional[str] = None

    # --- Tracking (P2) ---
    materialization_tracking: bool = False
    materialization_history: list[MaterializationSnapshot] = field(default_factory=list)
    first_flagged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "risk_type": self.risk_type.value,
            "description": self.description,
            "severity": self.severity.value,
            "related_tickers": self.related_tickers,
            "linked_decision_id": self.linked_decision_id,
            "materialization_tracking": self.materialization_tracking,
            "materialization_history": [s.to_dict() for s in self.materialization_history],
            "first_flagged_at": self.first_flagged_at.isoformat() if self.first_flagged_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Risk:
        base = cls.base_from_dict(data)
        first_flagged = data.get("first_flagged_at")
        resolved = data.get("resolved_at")
        return cls(
            **base,
            risk_type=RiskType(data.get("risk_type", "valuation")),
            description=data.get("description", ""),
            severity=Severity(data.get("severity", "medium")),
            related_tickers=data.get("related_tickers", []),
            linked_decision_id=data.get("linked_decision_id"),
            materialization_tracking=data.get("materialization_tracking", False),
            materialization_history=[MaterializationSnapshot.from_dict(s) for s in data.get("materialization_history", [])],
            first_flagged_at=datetime.fromisoformat(first_flagged) if first_flagged else None,
            resolved_at=datetime.fromisoformat(resolved) if resolved else None,
        )
