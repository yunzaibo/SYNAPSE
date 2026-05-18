"""EventContract — Links events to theses and positions with impact scores.

Part of the event-driven propagation graph (P3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from synapse.core.schemas.base import BaseSchema
from synapse.core.temporal import CST


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

    # --- Lifecycle (settled_at is new; created_at comes from BaseSchema) ---
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
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
        })
        return d

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
            propagation_depth=int(data.get("propagation_depth", 0)),
            settled_at=datetime.fromisoformat(settled_raw) if settled_raw else None,
        )
