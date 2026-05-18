"""Base Schema — Shared fields and dataclasses for all research objects.

Defines MarketContext and BaseSchema, the foundation for all 9 research objects.
Schema Evolution: Weak Schema + Lazy Upcast (P1 strategy, ADR-005).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional

from synapse.core.temporal import CST, MarketSession


# --- Enums shared across objects ---


class ObjectStatus(str, Enum):
    """Lifecycle status for all research objects."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    ABANDONED = "abandoned"
    SUPERSEDED = "superseded"


class SourceType(str, Enum):
    """Origin of the data in the object."""

    AI_GENERATED = "ai_generated"
    HUMAN_WRITTEN = "human_written"
    IMPORTED = "imported"
    MARKET_DATA = "market_data"


class CreatorType(str, Enum):
    """Who created the object."""

    AI = "ai"
    HUMAN = "human"
    MIXED = "mixed"


# --- Dataclasses ---


@dataclass
class MarketContext:
    """Market timing context for research objects.

    research_date ≠ market_date when events happen outside trading hours.
    """

    research_date: date
    market_date: date
    trading_session: MarketSession = MarketSession.NORMAL

    def to_dict(self) -> dict:
        return {
            "research_date": self.research_date.isoformat(),
            "market_date": self.market_date.isoformat(),
            "trading_session": self.trading_session.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MarketContext:
        return cls(
            research_date=date.fromisoformat(data["research_date"]),
            market_date=date.fromisoformat(data["market_date"]),
            trading_session=MarketSession(data.get("trading_session", "normal")),
        )


@dataclass
class BaseSchema:
    """Shared fields for all 9 research objects.

    Schema version enables Weak Schema + Lazy Upcast:
    - Read: schema 1.0 → runtime model (auto upcast)
    - Write: runtime → latest schema (always write latest)
    - No global migration script
    """

    id: str
    schema_version: str = "1.0"
    status: ObjectStatus = ObjectStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(CST))
    updated_at: datetime = field(default_factory=lambda: datetime.now(CST))
    source_type: SourceType = SourceType.HUMAN_WRITTEN
    created_by: CreatorType = CreatorType.HUMAN
    market_context: MarketContext = field(
        default_factory=lambda: MarketContext(
            research_date=date.today(),
            market_date=date.today(),
        )
    )

    def to_dict(self) -> dict:
        """Serialize to dict for YAML output."""
        return {
            "id": self.id,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "source_type": self.source_type.value,
            "created_by": self.created_by.value,
            "market_context": self.market_context.to_dict(),
        }

    @classmethod
    def base_from_dict(cls, data: dict) -> dict:
        """Extract BaseSchema fields from a dict, returning kwargs for construction."""
        mc_data = data.get("market_context", {})
        return {
            "id": data["id"],
            "schema_version": data.get("schema_version", "1.0"),
            "status": ObjectStatus(data.get("status", "active")),
            "created_at": datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(CST),
            "updated_at": datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(CST),
            "source_type": SourceType(data.get("source_type", "human_written")),
            "created_by": CreatorType(data.get("created_by", "human")),
            "market_context": MarketContext.from_dict(mc_data) if mc_data else MarketContext(
                research_date=date.today(),
                market_date=date.today(),
            ),
        }
