"""Position — Current holding.

Research-state-first, not P&L-first.
Position is a projection from Decision + market data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from synapse.core.schemas.base import BaseSchema


class ThesisStatus(str, Enum):
    ACTIVE = "active"
    WEAKENED = "weakened"
    INVALIDATED = "invalidated"


class AttentionState(str, Enum):
    STABLE = "stable"
    RISING = "rising"
    FADING = "fading"


@dataclass
class ResearchState:
    """Research-state tracking for a Position."""

    thesis_status: ThesisStatus = ThesisStatus.ACTIVE
    attention_state: AttentionState = AttentionState.STABLE
    last_review_date: Optional[date] = None

    def to_dict(self) -> dict:
        d = {
            "thesis_status": self.thesis_status.value,
            "attention_state": self.attention_state.value,
        }
        if self.last_review_date is not None:
            d["last_review_date"] = self.last_review_date.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ResearchState:
        return cls(
            thesis_status=ThesisStatus(data.get("thesis_status", "active")),
            attention_state=AttentionState(data.get("attention_state", "stable")),
            last_review_date=date.fromisoformat(data["last_review_date"]) if data.get("last_review_date") else None,
        )


@dataclass
class Position(BaseSchema):
    """Current holding — research state first, not P&L."""

    # --- Core ---
    ticker: str = ""
    symbol: str = ""
    market: str = ""

    # --- Thesis ---
    linked_thesis_id: Optional[str] = None
    thesis_at_entry: str = ""

    # --- Position State ---
    entry_date: Optional[date] = None
    entry_price: float = 0.0
    current_shares: int = 0

    # --- Research State ---
    research_state: ResearchState = field(default_factory=ResearchState)

    # --- Linked Records ---
    linked_decision_id: Optional[str] = None
    linked_watchlist_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "ticker": self.ticker,
            "symbol": self.symbol,
            "market": self.market,
            "linked_thesis_id": self.linked_thesis_id,
            "thesis_at_entry": self.thesis_at_entry,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "entry_price": self.entry_price,
            "current_shares": self.current_shares,
            "research_state": self.research_state.to_dict(),
            "linked_decision_id": self.linked_decision_id,
            "linked_watchlist_ids": self.linked_watchlist_ids,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Position:
        base = cls.base_from_dict(data)
        return cls(
            **base,
            ticker=data.get("ticker", ""),
            symbol=data.get("symbol", ""),
            market=data.get("market", ""),
            linked_thesis_id=data.get("linked_thesis_id"),
            thesis_at_entry=data.get("thesis_at_entry", ""),
            entry_date=date.fromisoformat(data["entry_date"]) if data.get("entry_date") else None,
            entry_price=data.get("entry_price", 0.0),
            current_shares=data.get("current_shares", 0),
            research_state=ResearchState.from_dict(data.get("research_state", {})),
            linked_decision_id=data.get("linked_decision_id"),
            linked_watchlist_ids=data.get("linked_watchlist_ids", []),
        )
