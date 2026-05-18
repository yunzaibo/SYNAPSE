"""Thesis — Research hypothesis/opinion.

Core object: all research connects through Thesis.
Supports append-only revision chain for evolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from synapse.core.schemas.base import BaseSchema


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Relevance(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    CONTEXTUAL = "contextual"


@dataclass
class RelatedSecurity:
    """A security linked to a Thesis."""

    ticker: str
    symbol: str
    market: str
    relevance: Relevance = Relevance.PRIMARY

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "symbol": self.symbol,
            "market": self.market,
            "relevance": self.relevance.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RelatedSecurity:
        return cls(
            ticker=data["ticker"],
            symbol=data["symbol"],
            market=data["market"],
            relevance=Relevance(data.get("relevance", "primary")),
        )


@dataclass
class Evidence:
    """Evidence supporting a Thesis."""

    type: str = ""
    description: str = ""
    source_type: str = ""
    linked_data_id: Optional[str] = None
    linked_event_id: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "type": self.type,
            "description": self.description,
            "source_type": self.source_type,
        }
        if self.linked_data_id is not None:
            d["linked_data_id"] = self.linked_data_id
        if self.linked_event_id is not None:
            d["linked_event_id"] = self.linked_event_id
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Evidence:
        return cls(
            type=data.get("type", ""),
            description=data.get("description", ""),
            source_type=data.get("source_type", ""),
            linked_data_id=data.get("linked_data_id"),
            linked_event_id=data.get("linked_event_id"),
        )


@dataclass
class Thesis(BaseSchema):
    """Research hypothesis — the core connective object."""

    # --- Core ---
    slug: str = ""
    title: str = ""
    summary: str = ""
    thesis_statement: str = ""

    # --- Related Securities ---
    related_securities: list[RelatedSecurity] = field(default_factory=list)

    # --- Research Topic ---
    topic_id: Optional[str] = None

    # --- Evidence ---
    evidence: list[Evidence] = field(default_factory=list)

    # --- Confidence ---
    confidence: Confidence = Confidence.MEDIUM

    # --- Thesis Evolution (append-only) ---
    parent_thesis_id: Optional[str] = None
    revision: int = 1
    previous_revision: Optional[str] = None

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "slug": self.slug,
            "title": self.title,
            "summary": self.summary,
            "thesis_statement": self.thesis_statement,
            "related_securities": [rs.to_dict() for rs in self.related_securities],
            "topic_id": self.topic_id,
            "evidence": [e.to_dict() for e in self.evidence],
            "confidence": self.confidence.value,
            "parent_thesis_id": self.parent_thesis_id,
            "revision": self.revision,
            "previous_revision": self.previous_revision,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Thesis:
        base = cls.base_from_dict(data)
        return cls(
            **base,
            slug=data.get("slug", ""),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            thesis_statement=data.get("thesis_statement", ""),
            related_securities=[RelatedSecurity.from_dict(rs) for rs in data.get("related_securities", [])],
            topic_id=data.get("topic_id"),
            evidence=[Evidence.from_dict(e) for e in data.get("evidence", [])],
            confidence=Confidence(data.get("confidence", "medium")),
            parent_thesis_id=data.get("parent_thesis_id"),
            revision=data.get("revision", 1),
            previous_revision=data.get("previous_revision"),
        )
