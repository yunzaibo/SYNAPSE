"""PropagationEdge -- Directed graph edge for event propagation.

Part of the event-driven propagation graph (P3).
Note: source_type/target_type renamed to src_entity_type/tgt_entity_type
to avoid shadowing BaseSchema.source_type (SourceType enum).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from synapse.core.schemas.base import BaseSchema


@dataclass
class PropagationEdge(BaseSchema):
    """Directed edge in the event propagation graph."""

    schema_version: str = "1.0"

    # --- Identity ---
    edge_id: str = ""

    # --- Source node ---
    source_id: str = ""
    src_entity_type: str = ""  # "event" | "thesis"

    # --- Target node ---
    target_id: str = ""
    tgt_entity_type: str = ""  # "thesis" | "position"

    # --- Edge properties ---
    weight: float = 0.5
    decay_rate: float = 0.1
    edge_type: str = ""

    def __post_init__(self) -> None:
        self._validate_range("weight", self.weight, 0.0, 1.0)

    @staticmethod
    def _validate_range(name: str, value: float, lo: float, hi: float) -> None:
        if not (lo <= value <= hi):
            raise ValueError(f"{name} must be in [{lo}, {hi}], got {value}")

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "src_entity_type": self.src_entity_type,
            "target_id": self.target_id,
            "tgt_entity_type": self.tgt_entity_type,
            "weight": self.weight,
            "decay_rate": self.decay_rate,
            "edge_type": self.edge_type,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> PropagationEdge:
        base = cls.base_from_dict(data)
        return cls(
            **base,
            edge_id=data.get("edge_id", ""),
            source_id=data.get("source_id", ""),
            src_entity_type=data.get("src_entity_type", ""),
            target_id=data.get("target_id", ""),
            tgt_entity_type=data.get("tgt_entity_type", ""),
            weight=float(data.get("weight", 0.5)),
            decay_rate=float(data.get("decay_rate", 0.1)),
            edge_type=data.get("edge_type", ""),
        )
