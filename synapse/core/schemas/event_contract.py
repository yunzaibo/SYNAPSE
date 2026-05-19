"""EventContract — Links events to theses and positions with impact scores.

Part of the event-driven propagation graph (P3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from synapse.core.schemas.base import BaseSchema
from synapse.core.temporal import CST


class SettlementStatus(str, Enum):
    """Settlement status for event contracts."""
    PENDING = "pending"
    SETTLED = "settled"
    EXPIRED = "expired"
    DISPUTED = "disputed"


@dataclass
class EventContract(BaseSchema):
    """Contract binding an event to affected theses/positions with impact scores."""

    schema_version: str = "1.0"

    # --- Identity ---
    contract_id: str = ""
    event_id: str = ""

    # --- Affected entities ---
    affected_theses: list[str] = field(default_factory=list)
    affected_positions: list[str] = field(default_factory=list)

    # --- Impact ---
    impact_scores: dict[str, float] = field(default_factory=dict)
    aggregate_impact: float = 0.0

    # --- Propagation ---
    propagation_depth: int = 0

    # --- Settlement lifecycle ---
    settlement_status: SettlementStatus = SettlementStatus.PENDING
    settlement_result: Optional[str] = None
    settlement_metadata: dict[str, Any] = field(default_factory=dict)
    settled_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "contract_id": self.contract_id,
            "event_id": self.event_id,
            "affected_theses": self.affected_theses,
            "affected_positions": self.affected_positions,
            "impact_scores": self.impact_scores,
            "aggregate_impact": self.aggregate_impact,
            "propagation_depth": self.propagation_depth,
            "settlement_status": self.settlement_status.value,
            "settlement_result": self.settlement_result,
            "settlement_metadata": self.settlement_metadata,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
        })
        return d

    def settle(
        self,
        result: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Settle the contract with a result.

        Sets status to SETTLED, records result and metadata, timestamps settled_at.
        """
        self.settlement_status = SettlementStatus.SETTLED
        self.settlement_result = result
        if metadata:
            self.settlement_metadata = metadata
        self.settled_at = datetime.now(tz=CST)

    def expire(self) -> None:
        """Expire the contract (timeout or stuck protection).

        Sets status to EXPIRED and timestamps settled_at.
        """
        self.settlement_status = SettlementStatus.EXPIRED
        self.settled_at = datetime.now(tz=CST)

    @classmethod
    def from_dict(cls, data: dict) -> EventContract:
        base = cls.base_from_dict(data)
        settled_raw = data.get("settled_at")
        return cls(
            **base,
            contract_id=data.get("contract_id", ""),
            event_id=data.get("event_id", ""),
            affected_theses=data.get("affected_theses", []),
            affected_positions=data.get("affected_positions", []),
            impact_scores=data.get("impact_scores", {}),
            aggregate_impact=float(data.get("aggregate_impact", 0.0)),
            settlement_status=SettlementStatus(data.get("settlement_status", "pending")),
            settlement_result=data.get("settlement_result"),
            settlement_metadata=data.get("settlement_metadata", {}),
            propagation_depth=int(data.get("propagation_depth", 0)),
            settled_at=datetime.fromisoformat(settled_raw) if settled_raw else None,
        )
