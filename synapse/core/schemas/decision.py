"""Decision — Buy/Sell decision record.

Natural security-bound: frozen cognitive state at decision time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from synapse.core.schemas.base import BaseSchema


class DecisionType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TimeHorizon(str, Enum):
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class AttentionOrigin(str, Enum):
    EVENT_ATTENTION = "event_attention"
    FACTOR_SIGNAL = "factor_signal"
    PORTFOLIO_REVIEW = "portfolio_review"


@dataclass
class DecisionSignal:
    """Signal linked to a decision."""

    linked_signal_id: str
    role: str = "primary"  # primary | supporting

    def to_dict(self) -> dict:
        return {"linked_signal_id": self.linked_signal_id, "role": self.role}

    @classmethod
    def from_dict(cls, data: dict) -> DecisionSignal:
        return cls(
            linked_signal_id=data["linked_signal_id"],
            role=data.get("role", "primary"),
        )


@dataclass
class Decision(BaseSchema):
    """Buy/sell decision — frozen cognitive state."""

    # --- Core ---
    ticker: str = ""
    symbol: str = ""
    market: str = ""
    decision_type: DecisionType = DecisionType.BUY

    # --- Thesis ---
    thesis: str = ""
    linked_thesis_id: Optional[str] = None

    # --- Risk ---
    key_risk: str = ""

    # --- Time Horizon ---
    time_horizon: TimeHorizon = TimeHorizon.MEDIUM_TERM

    # --- Attention Origin ---
    attention_origin: AttentionOrigin = AttentionOrigin.EVENT_ATTENTION

    # --- Position Link ---
    linked_position_id: Optional[str] = None

    # --- Signals ---
    signals: list[DecisionSignal] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "ticker": self.ticker,
            "symbol": self.symbol,
            "market": self.market,
            "decision_type": self.decision_type.value,
            "thesis": self.thesis,
            "linked_thesis_id": self.linked_thesis_id,
            "key_risk": self.key_risk,
            "time_horizon": self.time_horizon.value,
            "attention_origin": self.attention_origin.value,
            "linked_position_id": self.linked_position_id,
            "signals": [s.to_dict() for s in self.signals],
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Decision:
        base = cls.base_from_dict(data)
        return cls(
            **base,
            ticker=data.get("ticker", ""),
            symbol=data.get("symbol", ""),
            market=data.get("market", ""),
            decision_type=DecisionType(data.get("decision_type", "buy")),
            thesis=data.get("thesis", ""),
            linked_thesis_id=data.get("linked_thesis_id"),
            key_risk=data.get("key_risk", ""),
            time_horizon=TimeHorizon(data.get("time_horizon", "medium_term")),
            attention_origin=AttentionOrigin(data.get("attention_origin", "event_attention")),
            linked_position_id=data.get("linked_position_id"),
            signals=[DecisionSignal.from_dict(s) for s in data.get("signals", [])],
        )
