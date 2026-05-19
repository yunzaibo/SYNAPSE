"""EventExtractor -- Chinese financial event extraction engine.

Extracts structured events from unstructured Chinese financial text.
Classifies 5 event types (EARNINGS_FORECAST, MERGER_ACQUISITION, EQUITY_CHANGE,
POLICY_CHANGE, DIVIDEND), extracts trigger phrases with character offsets,
identifies participants via NER, and maps to P3 EventType taxonomy.

Part of P4 Chinese Financial NLP Layer (F-042).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from synapse.nlp.schemas import NEREntity, NERResult, TextDocument
from synapse.nlp.text_preprocessor import TextPreprocessor
from synapse.nlp.event_patterns import (
    ALL_TRIGGER_PATTERNS,
    EVENT_TYPE_TO_P3,
    EVENT_TYPE_KEYWORDS,
    TriggerPattern,
)
from synapse.nlp.ner_engine import NEREngine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Amount extraction helpers
# ---------------------------------------------------------------------------

def _extract_amount_from_text(text: str) -> Optional[float]:
    """Extract a numeric monetary amount from text around a trigger match.

    Searches the local context (50 chars before/after) for patterns like
    '100亿元', '5.5万元', '3000万', '50%'.
    """
    import re

    amount_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*(亿元|万元|万亿|千万|百万|万|千|百|美元|港元)"
    )
    scale_map = {
        "亿元": 1e8, "万元": 1e4, "万亿": 1e12, "千万": 1e7,
        "百万": 1e6, "万": 1e4, "千": 1e3, "百": 1e2,
        "美元": 1.0, "港元": 1.0,
    }

    matches = list(amount_pattern.finditer(text))
    if not matches:
        # Try percentage
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if pct_match:
            return float(pct_match.group(1)) / 100.0
        return None

    # Return the first matched amount
    m = matches[0]
    value = float(m.group(1)) * scale_map.get(m.group(2), 1.0)
    return value


def _extract_date_from_text(text: str) -> Optional[date]:
    """Extract a date from text around a trigger match."""
    import re

    # YYYY年MM月DD日
    match = re.search(r"(\d{4})\u5e74(\d{1,2})\u6708(\d{1,2})\u65e5", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    # YYYY-MM-DD
    match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    return None


def _extract_participants(
    text: str, match_start: int, match_end: int, ner_entities: tuple[NEREntity, ...],
    context_window: int = 50,
) -> tuple[str, ...]:
    """Extract participant names from NER entities near a trigger match.

    Looks for entities within `context_window` characters of the trigger span.
    """
    participants: list[str] = []
    window_start = max(0, match_start - context_window)
    window_end = min(len(text), match_end + context_window)

    for entity in ner_entities:
        # Entity must overlap or be within the context window
        if entity.start_offset < window_end and entity.end_offset > window_start:
            if entity.entity_type in ("company", "person", "institution"):
                if entity.surface_form not in participants:
                    participants.append(entity.surface_form)

    return tuple(participants)


# ---------------------------------------------------------------------------
# Extraction result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ExtractedEvent:
    """A single extracted event from financial text.

    Attributes
    ----------
    event_type:
        Internal event type name (e.g. "EARNINGS_FORECAST").
    trigger_phrase:
        The text span that triggered event detection.
    participants:
        Tuple of entity names involved in the event.
    amount:
        Monetary value if mentioned in the text (None if not applicable).
    date:
        Event date if mentioned (None if not applicable).
    confidence:
        Confidence score in [0.0, 1.0].
    entity_spans:
        Tuple of (start, end, entity_type) tuples for linked entities.
    """

    event_type: str = ""
    trigger_phrase: str = ""
    participants: tuple[str, ...] = ()
    amount: Optional[float] = None
    date: Optional[date] = None
    confidence: float = 0.0
    entity_spans: tuple[tuple[int, int, str], ...] = ()

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "trigger_phrase": self.trigger_phrase,
            "participants": list(self.participants),
            "amount": self.amount,
            "date": self.date.isoformat() if self.date else None,
            "confidence": self.confidence,
            "entity_spans": [list(s) for s in self.entity_spans],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ExtractedEvent:
        date_val = None
        if data.get("date"):
            try:
                date_val = date.fromisoformat(data["date"])
            except (ValueError, TypeError):
                pass

        return cls(
            event_type=data.get("event_type", ""),
            trigger_phrase=data.get("trigger_phrase", ""),
            participants=tuple(data.get("participants", [])),
            amount=float(data["amount"]) if data.get("amount") is not None else None,
            date=date_val,
            confidence=float(data.get("confidence", 0.0)),
            entity_spans=tuple(
                (s[0], s[1], s[2]) for s in data.get("entity_spans", [])
            ),
        )


@dataclass(frozen=True, slots=True)
class EventExtractionResult:
    """Result of event extraction from a document.

    Attributes
    ----------
    events:
        Tuple of extracted events (immutable).
    processing_time_ms:
        Time taken to process the document in milliseconds.
    """

    events: tuple[ExtractedEvent, ...] = ()
    processing_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "events": [e.to_dict() for e in self.events],
            "processing_time_ms": self.processing_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EventExtractionResult:
        return cls(
            events=tuple(
                ExtractedEvent.from_dict(e) for e in data.get("events", [])
            ),
            processing_time_ms=float(data.get("processing_time_ms", 0.0)),
        )


# ---------------------------------------------------------------------------
# EventExtractor
# ---------------------------------------------------------------------------

@dataclass
class EventExtractor:
    """Chinese financial event extraction engine.

    Pipeline:
    1. Text preprocessing (abbreviation expansion)
    2. NER entity recognition
    3. Pattern matching for event triggers
    4. Event type classification
    5. Detail extraction (amount, date, participants)
    6. Map to P3 EventType string
    """

    preprocessor: TextPreprocessor = field(default_factory=TextPreprocessor)
    ner_engine: NEREngine = field(default_factory=NEREngine)

    def extract(self, doc: TextDocument) -> EventExtractionResult:
        """Extract structured events from a financial text document.

        Parameters
        ----------
        doc:
            Input TextDocument with Chinese financial text.

        Returns
        -------
        EventExtractionResult with all extracted events and timing.
        """
        start_time = time.monotonic()

        if not doc.text:
            return EventExtractionResult(events=(), processing_time_ms=0.0)

        text = doc.text

        # Step 1: Preprocess text
        preprocessed = self.preprocessor.preprocess(text)

        # Step 2: Run NER for entity recognition
        ner_result = self.ner_engine.recognize(doc)

        # Step 3 & 4: Match trigger patterns and classify event type
        events = self._match_and_classify(text, ner_result)

        elapsed_ms = (time.monotonic() - start_time) * 1000

        return EventExtractionResult(
            events=tuple(events),
            processing_time_ms=round(elapsed_ms, 2),
        )

    def _match_and_classify(
        self, text: str, ner_result: NERResult,
    ) -> list[ExtractedEvent]:
        """Match trigger patterns, classify events, extract details."""
        events: list[ExtractedEvent] = []
        seen_spans: set[tuple[int, int]] = set()

        # Pattern-based matching
        for trigger in ALL_TRIGGER_PATTERNS:
            for match in trigger.pattern.finditer(text):
                span = (match.start(), match.end())
                if span in seen_spans:
                    continue
                seen_spans.add(span)

                trigger_phrase = match.group(0)

                # Extract details
                participants = _extract_participants(
                    text, match.start(), match.end(), ner_result.entities,
                )
                amount = _extract_amount_from_text(trigger_phrase)
                event_date = _extract_date_from_text(text)

                # Entity spans near the trigger
                entity_spans = self._collect_entity_spans(
                    text, match.start(), match.end(), ner_result.entities,
                )

                event = ExtractedEvent(
                    event_type=trigger.event_type,
                    trigger_phrase=trigger_phrase,
                    participants=participants,
                    amount=amount,
                    date=event_date,
                    confidence=trigger.base_confidence,
                    entity_spans=entity_spans,
                )
                events.append(event)

        # Keyword-based fallback (only if no pattern matched)
        if not events:
            keyword_events = self._classify_by_keywords(text, ner_result)
            events.extend(keyword_events)

        # Deduplicate by event_type + trigger_phrase
        events = self._deduplicate_events(events)

        return events

    def _classify_by_keywords(
        self, text: str, ner_result: NERResult,
    ) -> list[ExtractedEvent]:
        """Fallback keyword-based event classification."""
        events: list[ExtractedEvent] = []

        for event_type, keywords in EVENT_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    idx = text.index(kw)
                    # Find the sentence around this keyword
                    sentence = self._extract_sentence_context(text, idx)

                    participants = _extract_participants(
                        text, idx, idx + len(kw), ner_result.entities,
                    )
                    amount = _extract_amount_from_text(sentence)
                    event_date = _extract_date_from_text(sentence)
                    entity_spans = self._collect_entity_spans(
                        text, idx, idx + len(kw), ner_result.entities,
                    )

                    event = ExtractedEvent(
                        event_type=event_type,
                        trigger_phrase=kw,
                        participants=participants,
                        amount=amount,
                        date=event_date,
                        confidence=0.60,  # lower confidence for keyword match
                        entity_spans=entity_spans,
                    )
                    events.append(event)
                    break  # one event per type from keyword fallback

        return events

    @staticmethod
    def _extract_sentence_context(text: str, idx: int, window: int = 50) -> str:
        """Extract a sentence-sized context around an index."""
        start = max(0, idx - window)
        end = min(len(text), idx + window)
        return text[start:end]

    @staticmethod
    def _collect_entity_spans(
        text: str, match_start: int, match_end: int,
        entities: tuple[NEREntity, ...], context_window: int = 50,
    ) -> tuple[tuple[int, int, str], ...]:
        """Collect entity spans near a trigger match."""
        spans: list[tuple[int, int, str]] = []
        window_start = max(0, match_start - context_window)
        window_end = min(len(text), match_end + context_window)

        for entity in entities:
            if entity.start_offset < window_end and entity.end_offset > window_start:
                span = (entity.start_offset, entity.end_offset, entity.entity_type)
                if span not in spans:
                    spans.append(span)

        return tuple(spans)

    @staticmethod
    def _deduplicate_events(events: list[ExtractedEvent]) -> list[ExtractedEvent]:
        """Deduplicate events with same type and trigger phrase."""
        seen: set[tuple[str, str]] = set()
        result: list[ExtractedEvent] = []

        for event in events:
            key = (event.event_type, event.trigger_phrase)
            if key not in seen:
                seen.add(key)
                result.append(event)

        return result

    @staticmethod
    def get_p3_event_type(event_type: str) -> str:
        """Map internal event type to P3 EventType string.

        Parameters
        ----------
        event_type:
            Internal event type name (e.g. "EARNINGS_FORECAST").

        Returns
        -------
        P3 EventType string (e.g. "earnings").
        """
        return EVENT_TYPE_TO_P3.get(event_type, "earnings")
