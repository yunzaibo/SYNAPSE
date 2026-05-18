"""WatchlistEntry — Daily research queue item.

One WatchlistEntry = "one thing worth researching today".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from synapse.core.schemas.base import BaseSchema


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


class TriggerType(str, Enum):
    EVENT_ATTENTION = "event_attention"
    FACTOR_SIGNAL = "factor_signal"
    PORTFOLIO_REVIEW = "portfolio_review"
    SECTOR_ROTATION = "sector_rotation"


@dataclass
class WatchlistSignal:
    """A signal within a WatchlistEntry."""

    type: SignalType
    strength: SignalStrength
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "strength": self.strength.value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> WatchlistSignal:
        return cls(
            type=SignalType(data["type"]),
            strength=SignalStrength(data["strength"]),
            description=data.get("description", ""),
        )


@dataclass
class WatchlistEntry(BaseSchema):
    """Daily research queue item — "today worth researching"."""

    # --- Core ---
    ticker: str = ""
    symbol: str = ""
    market: str = ""
    headline: str = ""
    why_now: str = ""

    # --- Signals ---
    signals: list[WatchlistSignal] = field(default_factory=list)

    # --- Research Angle ---
    research_angle: str = ""
    action: str = "值得关注"

    # --- Risk Hint ---
    risk_hint: str = ""

    # --- Trigger Type ---
    trigger_type: TriggerType = TriggerType.EVENT_ATTENTION

    # --- Links ---
    linked_thesis_id: Optional[str] = None
    linked_event_id: Optional[str] = None

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "ticker": self.ticker,
            "symbol": self.symbol,
            "market": self.market,
            "headline": self.headline,
            "why_now": self.why_now,
            "signals": [s.to_dict() for s in self.signals],
            "research_angle": self.research_angle,
            "action": self.action,
            "risk_hint": self.risk_hint,
            "trigger_type": self.trigger_type.value,
            "linked_thesis_id": self.linked_thesis_id,
            "linked_event_id": self.linked_event_id,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> WatchlistEntry:
        base = cls.base_from_dict(data)
        return cls(
            **base,
            ticker=data.get("ticker", ""),
            symbol=data.get("symbol", ""),
            market=data.get("market", ""),
            headline=data.get("headline", ""),
            why_now=data.get("why_now", ""),
            signals=[WatchlistSignal.from_dict(s) for s in data.get("signals", [])],
            research_angle=data.get("research_angle", ""),
            action=data.get("action", "值得关注"),
            risk_hint=data.get("risk_hint", ""),
            trigger_type=TriggerType(data.get("trigger_type", "event_attention")),
            linked_thesis_id=data.get("linked_thesis_id"),
            linked_event_id=data.get("linked_event_id"),
        )
