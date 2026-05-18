"""ResearchTopic — Clustering tag for theses.

P1: tags代替, 不独立管理. Supports topic hierarchy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from synapse.core.schemas.base import BaseSchema


@dataclass
class ResearchTopic(BaseSchema):
    """Clustering tag for theses — supports hierarchy."""

    # --- Core ---
    slug: str = ""
    name: str = ""
    description: str = ""
    parent_topic_id: Optional[str] = None

    # --- Related Theses ---
    thesis_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "parent_topic_id": self.parent_topic_id,
            "thesis_ids": self.thesis_ids,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ResearchTopic:
        base = cls.base_from_dict(data)
        return cls(
            **base,
            slug=data.get("slug", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            parent_topic_id=data.get("parent_topic_id"),
            thesis_ids=data.get("thesis_ids", []),
        )
