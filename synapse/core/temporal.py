"""Temporal Semantics — Time-aware context for research objects.

ADR-008: All time-aware objects must declare three time dimensions:
- Event time: when the event actually happened
- Processing time: when the system processed it
- Market effective time: when the market considers it effective
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta
from enum import Enum
from typing import Optional


CST = timezone(timedelta(hours=8))


class MarketSession(str, Enum):
    """Market trading session status."""

    NORMAL = "normal"
    HALF_DAY = "half_day"
    HOLIDAY = "holiday"
    SUSPENDED = "suspended"


@dataclass
class TemporalContext:
    """Time-aware context for all research objects.

    Enforces ADR-008 temporal semantics:
    - event_time + event_timezone: when the event actually happened
    - market_date + market_session: market effective time
    - created_at + updated_at: processing time
    - available_at + as_of_date: data availability
    """

    # --- Required ---
    event_time: datetime
    market_date: date

    # --- Event Time ---
    event_timezone: str = "Asia/Shanghai"

    # --- Market Effective Time ---
    market_session: MarketSession = MarketSession.NORMAL

    # --- Processing Time ---
    created_at: datetime = field(default_factory=lambda: datetime.now(CST))
    updated_at: datetime = field(default_factory=lambda: datetime.now(CST))

    # --- Availability ---
    available_at: Optional[datetime] = None
    as_of_date: Optional[date] = None

    def __post_init__(self) -> None:
        if self.event_timezone != "Asia/Shanghai":
            raise ValueError(
                f"P1 only supports Asia/Shanghai timezone, got {self.event_timezone!r}"
            )
        if isinstance(self.event_time, datetime) and self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware (use ISO 8601)")
        if isinstance(self.created_at, datetime) and self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if isinstance(self.updated_at, datetime) and self.updated_at.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware")
        if self.available_at is not None and isinstance(self.available_at, datetime) and self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")

    @classmethod
    def create(
        cls,
        event_time: datetime,
        market_date: date,
        market_session: MarketSession = MarketSession.NORMAL,
        event_timezone: str = "Asia/Shanghai",
    ) -> TemporalContext:
        """Factory method with minimal required fields."""
        return cls(
            event_time=event_time,
            event_timezone=event_timezone,
            market_date=market_date,
            market_session=market_session,
        )

    def with_updated(self) -> TemporalContext:
        """Return a copy with updated_at set to now."""
        self.updated_at = datetime.now(CST)
        return self

    def mark_available(self, available_at: datetime) -> None:
        """Mark when data became available."""
        self.available_at = available_at

    def set_as_of(self, as_of: date) -> None:
        """Set the as-of date for data cutoff."""
        self.as_of_date = as_of

    def to_dict(self) -> dict:
        """Serialize to dict for YAML/JSON."""
        result = {
            "event_time": self.event_time.isoformat(),
            "event_timezone": self.event_timezone,
            "market_date": self.market_date.isoformat(),
            "market_session": self.market_session.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if self.available_at is not None:
            result["available_at"] = self.available_at.isoformat()
        if self.as_of_date is not None:
            result["as_of_date"] = self.as_of_date.isoformat()
        return result
