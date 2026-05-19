"""NLP Schemas -- Frozen dataclasses for NER input/output.

TextDocument: input document for NER processing.
NEREntity: a single recognized entity with offsets and metadata.
NERResult: complete NER output with all entities and timing.

All dataclasses use frozen=True, slots=True for immutability and memory efficiency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class TextDocument:
    """Input document for NER processing.

    Attributes
    ----------
    text:
        Raw Chinese text to process.
    doc_id:
        Unique document identifier.
    source_type:
        Origin of the text (e.g. "news", "announcement", "research_report").
    metadata:
        Additional metadata (e.g. publish_date, author).
    """

    text: str = ""
    doc_id: str = ""
    source_type: str = "unknown"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "doc_id": self.doc_id,
            "source_type": self.source_type,
            "metadata": dict(self.metadata) if self.metadata else {},
        }

    @classmethod
    def from_dict(cls, data: dict) -> TextDocument:
        return cls(
            text=data.get("text", ""),
            doc_id=data.get("doc_id", ""),
            source_type=data.get("source_type", "unknown"),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class NEREntity:
    """A single recognized named entity.

    Attributes
    ----------
    surface_form:
        The matched text span (e.g. "贵州茅台").
    entity_type:
        Entity type: "company", "person", "product", "institution", or "metric".
    start_offset:
        Character-level start index (inclusive) in the original text.
    end_offset:
        Character-level end index (exclusive) in the original text.
    confidence:
        Confidence score in [0.0, 1.0].
    linked_ticker:
        Stock ticker linked to company entities (e.g. "600519.SH"). None for non-company.
    normalized_name:
        Standard/normalized form (e.g. "贵州茅台酒股份有限公司"). None if not applicable.
    """

    surface_form: str = ""
    entity_type: str = ""
    start_offset: int = 0
    end_offset: int = 0
    confidence: float = 0.0
    linked_ticker: Optional[str] = None
    normalized_name: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "surface_form": self.surface_form,
            "entity_type": self.entity_type,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "confidence": self.confidence,
            "linked_ticker": self.linked_ticker,
            "normalized_name": self.normalized_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NEREntity:
        return cls(
            surface_form=data.get("surface_form", ""),
            entity_type=data.get("entity_type", ""),
            start_offset=int(data.get("start_offset", 0)),
            end_offset=int(data.get("end_offset", 0)),
            confidence=float(data.get("confidence", 0.0)),
            linked_ticker=data.get("linked_ticker"),
            normalized_name=data.get("normalized_name"),
        )


@dataclass(frozen=True, slots=True)
class NERResult:
    """Complete NER output for a document.

    Attributes
    ----------
    doc_id:
        Identifier of the processed document.
    entities:
        Tuple of recognized entities (immutable).
    processing_time_ms:
        Time taken to process the document in milliseconds.
    """

    doc_id: str = ""
    entities: tuple[NEREntity, ...] = ()
    processing_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "entities": [e.to_dict() for e in self.entities],
            "processing_time_ms": self.processing_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NERResult:
        return cls(
            doc_id=data.get("doc_id", ""),
            entities=tuple(NEREntity.from_dict(e) for e in data.get("entities", [])),
            processing_time_ms=float(data.get("processing_time_ms", 0.0)),
        )
