"""Signal — Independent signal record.

P1: recorded in Watchlist/Decision only, no independent decay tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from synapse.core.schemas.base import BaseSchema
from synapse.analytics.tracking_models import DecaySnapshot


class SignalType(str, Enum):
    ATTENTION_SPIKE = "attention_spike"
    SECTOR_RESONANCE = "sector_resonance"
    HISTORICAL_PATTERN_MATCH = "historical_pattern_match"
    FACTOR_ANOMALY = "factor_anomaly"
    EARNINGS_SURPRISE = "earnings_surprise"
    POLICY_IMPACT = "policy_impact"


class SignalStrength(str, Enum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


@dataclass
class Signal(BaseSchema):
    """Independent signal record."""

    schema_version: str = "2.0"

    # --- Core ---
    signal_type: SignalType = SignalType.ATTENTION_SPIKE
    strength: SignalStrength = SignalStrength.MEDIUM
    description: str = ""

    # --- Related ---
    related_tickers: list[str] = field(default_factory=list)
    linked_event_id: Optional[str] = None

    # --- Decay (P2) ---
    decay_tracking: bool = False
    decay_history: list[DecaySnapshot] = field(default_factory=list)
    first_seen_at: Optional[datetime] = None
    last_evaluated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "signal_type": self.signal_type.value,
            "strength": self.strength.value,
            "description": self.description,
            "related_tickers": self.related_tickers,
            "linked_event_id": self.linked_event_id,
            "decay_tracking": self.decay_tracking,
            "decay_history": [s.to_dict() for s in self.decay_history],
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_evaluated_at": self.last_evaluated_at.isoformat() if self.last_evaluated_at else None,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Signal:
        base = cls.base_from_dict(data)
        first_seen = data.get("first_seen_at")
        last_eval = data.get("last_evaluated_at")
        return cls(
            **base,
            signal_type=SignalType(data.get("signal_type", "attention_spike")),
            strength=SignalStrength(data.get("strength", "medium")),
            description=data.get("description", ""),
            related_tickers=data.get("related_tickers", []),
            linked_event_id=data.get("linked_event_id"),
            decay_tracking=data.get("decay_tracking", False),
            decay_history=[DecaySnapshot.from_dict(s) for s in data.get("decay_history", [])],
            first_seen_at=datetime.fromisoformat(first_seen) if first_seen else None,
            last_evaluated_at=datetime.fromisoformat(last_eval) if last_eval else None,
        )
