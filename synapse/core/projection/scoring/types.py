"""Scoring Engine Types — Data structures for the watchlist scoring pipeline.

ScoringContext carries all inputs needed by scoring functions.
ScoredEntry wraps a WatchlistEntry with its computed score and reason.
ScoringResult aggregates scored entries with metadata for traceability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from synapse.core.schemas.event import Event
from synapse.core.schemas.position import Position
from synapse.core.schemas.signal import Signal
from synapse.core.schemas.watchlist import WatchlistEntry
from synapse.core.temporal import CST


@dataclass
class MarketData:
    """Market-level data available to scoring functions.

    Missing market data is treated as neutral (0.5) rather than 0.0,
    since absence of market info should not penalize a stock.
    """

    sentiment_score: float = 0.5
    breadth_score: float = 0.5
    volatility_score: float = 0.5

    def to_dict(self) -> dict:
        return {
            "sentiment_score": self.sentiment_score,
            "breadth_score": self.breadth_score,
            "volatility_score": self.volatility_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MarketData:
        return cls(
            sentiment_score=float(data.get("sentiment_score", 0.5)),
            breadth_score=float(data.get("breadth_score", 0.5)),
            volatility_score=float(data.get("volatility_score", 0.5)),
        )


@dataclass
class ScoringContext:
    """Immutable context passed to every scoring function.

    Aggregates all data sources needed to score a single WatchlistEntry.
    """

    events: list[Event] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    target_date: date = field(default_factory=date.today)
    config: dict[str, Any] = field(default_factory=dict)
    market_data: Optional[MarketData] = None

    def to_dict(self) -> dict:
        return {
            "events": [e.to_dict() for e in self.events],
            "signals": [s.to_dict() for s in self.signals],
            "positions": [p.to_dict() for p in self.positions],
            "target_date": self.target_date.isoformat(),
            "config": self.config,
            "market_data": self.market_data.to_dict() if self.market_data else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScoringContext:
        return cls(
            events=[Event.from_dict(e) for e in data.get("events", [])],
            signals=[Signal.from_dict(s) for s in data.get("signals", [])],
            positions=[Position.from_dict(p) for p in data.get("positions", [])],
            target_date=date.fromisoformat(data["target_date"]) if "target_date" in data else date.today(),
            config=data.get("config", {}),
            market_data=MarketData.from_dict(data["market_data"]) if data.get("market_data") else None,
        )


@dataclass
class ScoredEntry:
    """A WatchlistEntry with its computed score and component breakdown.

    Attributes:
        entry: The original watchlist entry.
        total_score: Weighted aggregate score in [0.0, 1.0].
        component_scores: Individual dimension scores keyed by dimension name.
        reason: Human-readable explanation of why this score was assigned.
    """

    entry: WatchlistEntry
    total_score: float = 0.0
    component_scores: dict[str, float] = field(default_factory=dict)
    reason: str = ""

    def __post_init__(self) -> None:
        if not (0.0 <= self.total_score <= 1.0):
            raise ValueError(
                f"total_score must be in [0.0, 1.0], got {self.total_score}"
            )

    def to_dict(self) -> dict:
        return {
            "entry": self.entry.to_dict(),
            "total_score": self.total_score,
            "component_scores": self.component_scores,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScoredEntry:
        return cls(
            entry=WatchlistEntry.from_dict(data["entry"]),
            total_score=float(data.get("total_score", 0.0)),
            component_scores=data.get("component_scores", {}),
            reason=data.get("reason", ""),
        )


@dataclass
class ScoringResult:
    """Result of scoring a batch of watchlist entries.

    Provides traceability: which entries were scored, when, and with what config.
    """

    entries: list[ScoredEntry] = field(default_factory=list)
    target_date: date = field(default_factory=date.today)
    generation_timestamp: datetime = field(default_factory=lambda: datetime.now(CST))
    config_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "target_date": self.target_date.isoformat(),
            "generation_timestamp": self.generation_timestamp.isoformat(),
            "config_hash": self.config_hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScoringResult:
        return cls(
            entries=[ScoredEntry.from_dict(e) for e in data.get("entries", [])],
            target_date=date.fromisoformat(data["target_date"]) if "target_date" in data else date.today(),
            generation_timestamp=datetime.fromisoformat(data["generation_timestamp"]) if "generation_timestamp" in data else datetime.now(CST),
            config_hash=data.get("config_hash", ""),
        )
