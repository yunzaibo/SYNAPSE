"""NLP Detectors -- BaseDetector implementations wrapping NLP modules.

Connects all NLP outputs (F-037 through F-042) to the P3 event engine.
Each detector wraps an NLP module via lazy import to avoid circular dependencies.

Part of P4 NLP-P3 Event Integration (F-043).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional
import uuid

from synapse.core.schemas.event import (
    Event,
    EventSourceType,
    EventType,
    ImpactLevel,
    PropagationState,
)
from synapse.event.base import BaseDetector
from synapse.nlp.schemas import TextDocument

logger = logging.getLogger(__name__)


def _event_id() -> str:
    return str(uuid.uuid4())


def _text_to_doc(data: dict) -> TextDocument:
    """Extract a TextDocument from the data dict.

    Supports ``data["text"]`` (str) or ``data["document"]`` (TextDocument).
    """
    doc = data.get("document")
    if isinstance(doc, TextDocument):
        return doc
    text = data.get("text", "")
    return TextDocument(text=text)


def _extract_date(data: dict) -> Optional[date]:
    """Extract date from common field names in *data*."""
    for key in ("event_date", "date", "report_date"):
        val = data.get(key)
        if isinstance(val, str):
            try:
                return date.fromisoformat(val)
            except ValueError:
                continue
        if isinstance(val, date):
            return val
    return None


def _extract_tickers(data: dict) -> list[str]:
    """Extract ticker list from data dict."""
    tickers = data.get("tickers", [])
    if isinstance(tickers, list):
        return tickers
    return []


# ---------------------------------------------------------------------------
# AnnouncementDetector (F-037)
# ---------------------------------------------------------------------------


class AnnouncementDetector(BaseDetector):
    """Detects earnings announcements via AnnouncementParser.

    Wraps ``synapse.nlp.announcement_parser.AnnouncementParser``.
    Maps to ``EventType.EARNINGS``.

    Input data keys:
        - ``text`` (str) or ``document`` (TextDocument): Chinese announcement text.

    Returns None when:
        - No text provided.
        - AnnouncementParser finds no metrics, period, or entities.
    """

    @classmethod
    def event_type(cls) -> str:
        return "earnings"

    def detect(self, data: dict) -> Optional[Event]:
        text = data.get("text", "")
        if not text:
            return None

        try:
            from synapse.nlp.announcement_parser import AnnouncementParser
            parser = AnnouncementParser()
            doc = _text_to_doc(data)
            result = parser.parse(doc)
        except Exception:
            logger.debug("AnnouncementParser failed, degrading gracefully", exc_info=True)
            return None

        if not result.metrics and result.period_info is None:
            return None

        confidence = self.confidence_score(data, nlp_confidence=result.confidence)
        tickers = _extract_tickers(data)

        # Collect entity tickers
        for entity in result.entities:
            if entity.linked_ticker and entity.linked_ticker not in tickers:
                tickers.append(entity.linked_ticker)

        title_parts: list[str] = []
        if result.period_info:
            title_parts.append(result.period_info.period_label)
        if result.metrics:
            names = [m.name for m in result.metrics[:3]]
            title_parts.append(f"metrics: {', '.join(names)}")

        return Event(
            id=_event_id(),
            event_type=EventType.EARNINGS,
            title=f"Announcement: {', '.join(title_parts) if title_parts else 'earnings data'}",
            description=(
                f"Financial announcement parsed: "
                f"{len(result.metrics)} metrics, "
                f"{len(result.entities)} entities"
            ),
            event_date=_extract_date(data),
            related_tickers=tickers,
            confidence=confidence,
            severity=0.6,
            source=EventSourceType.NEWS,
        )

    def confidence_score(self, data: dict, nlp_confidence: float = 0.0) -> float:
        """Score based on NLP extraction confidence and text presence."""
        text = data.get("text", "")
        if not text:
            return 0.0
        # Base 0.3 for text, plus NLP confidence scaled to 0.7
        return min(0.3 + nlp_confidence * 0.7, 1.0)


# ---------------------------------------------------------------------------
# ResearchReportDetector (F-038)
# ---------------------------------------------------------------------------


class ResearchReportDetector(BaseDetector):
    """Detects analyst research reports via ReportSummarizer.

    Wraps ``synapse.nlp.report_summarizer.ReportSummarizer``.
    Maps to ``EventType.SOCIAL_SENTIMENT``.

    Input data keys:
        - ``text`` (str) or ``document`` (TextDocument): Chinese research report text.
    """

    @classmethod
    def event_type(cls) -> str:
        return "research_sentiment"

    def detect(self, data: dict) -> Optional[Event]:
        text = data.get("text", "")
        if not text:
            return None

        try:
            from synapse.nlp.report_summarizer import ReportSummarizer
            summarizer = ReportSummarizer()
            doc = _text_to_doc(data)
            result = summarizer.summarize(doc)
        except Exception:
            logger.debug("ReportSummarizer failed, degrading gracefully", exc_info=True)
            return None

        if not result.report_title and not result.thesis_summary:
            return None

        confidence = self.confidence_score(data)
        tickers = _extract_tickers(data)

        title = result.report_title or "Research report"
        parts = [title]
        if result.rating:
            parts.append(f"rating={result.rating.value}")
        if result.target_price:
            parts.append(f"target={result.target_price}")

        return Event(
            id=_event_id(),
            event_type=EventType.SOCIAL_SENTIMENT,
            title=f"Research: {', '.join(parts)}",
            description=(
                f"Research report by {result.analyst_name or 'unknown'} "
                f"({result.institution or 'unknown'}): "
                f"{result.thesis_summary[:100] if result.thesis_summary else 'N/A'}"
            ),
            event_date=_extract_date(data),
            related_tickers=tickers,
            confidence=confidence,
            severity=0.5,
            source=EventSourceType.NEWS,
        )

    def confidence_score(self, data: dict, nlp_confidence: float = 0.0) -> float:
        """Score based on report completeness."""
        text = data.get("text", "")
        if not text:
            return 0.0
        # Base 0.2 for text, up to 0.6 for having title+thesis
        score = 0.2 + nlp_confidence * 0.6
        return min(score, 1.0)


# ---------------------------------------------------------------------------
# NewsSentimentDetector (F-039)
# ---------------------------------------------------------------------------


class NewsSentimentDetector(BaseDetector):
    """Detects news sentiment signals via NewsSentimentClassifier.

    Wraps ``synapse.nlp.sentiment_classifier.NewsSentimentClassifier``.
    Maps to ``EventType.SOCIAL_SENTIMENT``.

    Input data keys:
        - ``text`` (str) or ``document`` (TextDocument): Chinese news text.

    Only fires for non-neutral sentiment (bullish/bearish).
    """

    @classmethod
    def event_type(cls) -> str:
        return "social_sentiment"

    def detect(self, data: dict) -> Optional[Event]:
        text = data.get("text", "")
        if not text:
            return None

        try:
            from synapse.nlp.sentiment_classifier import NewsSentimentClassifier
            classifier = NewsSentimentClassifier()
            result = classifier.classify(text)
        except Exception:
            logger.debug("NewsSentimentClassifier failed, degrading gracefully", exc_info=True)
            return None

        # Only fire for non-neutral sentiment
        if result.label == "neutral":
            return None

        confidence = self.confidence_score(data, nlp_confidence=result.confidence)
        tickers = _extract_tickers(data)

        return Event(
            id=_event_id(),
            event_type=EventType.SOCIAL_SENTIMENT,
            title=f"Sentiment: {result.label} (score={result.score:+.3f})",
            description=(
                f"News sentiment classified as {result.label}: "
                f"score={result.score:+.3f}, confidence={result.confidence:.3f}"
            ),
            event_date=_extract_date(data),
            related_tickers=tickers,
            confidence=confidence,
            severity=0.4,
            source=EventSourceType.NEWS,
        )

    def confidence_score(self, data: dict, nlp_confidence: float = 0.0) -> float:
        """Score based on sentiment confidence magnitude."""
        text = data.get("text", "")
        if not text:
            return 0.0
        return min(0.3 + nlp_confidence * 0.7, 1.0)


# ---------------------------------------------------------------------------
# PolicyDetector_NLP (F-040)
# ---------------------------------------------------------------------------


class PolicyDetector_NLP(BaseDetector):
    """Detects policy documents via PolicyUnderstander.

    Wraps ``synapse.nlp.policy_understander.PolicyUnderstander``.
    Maps to ``EventType.POLICY_CHANGE``.

    Input data keys:
        - ``text`` (str) or ``document`` (TextDocument): Chinese regulatory text.

    Named PolicyDetector_NLP to avoid conflict with existing PolicyDetector
    in synapse.event.detectors.
    """

    @classmethod
    def event_type(cls) -> str:
        return "policy_change"

    def detect(self, data: dict) -> Optional[Event]:
        text = data.get("text", "")
        if not text:
            return None

        try:
            from synapse.nlp.policy_understander import PolicyUnderstander
            understander = PolicyUnderstander()
            doc = _text_to_doc(data)
            result = understander.understand(doc)
        except Exception:
            logger.debug("PolicyUnderstander failed, degrading gracefully", exc_info=True)
            return None

        if result.issuing_body == "unknown" and not result.key_changes:
            return None

        confidence = self.confidence_score(data)
        tickers = _extract_tickers(data)

        body = result.issuing_body or "unknown"
        doc_type = result.document_type or "regulatory"
        sectors = ", ".join(result.affected_sectors[:3]) if result.affected_sectors else "N/A"

        return Event(
            id=_event_id(),
            event_type=EventType.POLICY_CHANGE,
            title=f"Policy: {body} {doc_type}",
            description=(
                f"Policy document from {body} ({doc_type}): "
                f"{len(result.key_changes)} changes, "
                f"sectors: {sectors}"
            ),
            event_date=_extract_date(data),
            related_tickers=tickers,
            confidence=confidence,
            severity=0.7,
            source=EventSourceType.NEWS,
        )

    def confidence_score(self, data: dict, nlp_confidence: float = 0.0) -> float:
        """Score based on issuing body recognition and text presence."""
        text = data.get("text", "")
        if not text:
            return 0.0
        # Official source detection adds confidence
        score = 0.3 + nlp_confidence * 0.6
        if any(kw in text for kw in ("证监会", "央行", "银保监", "国务院")):
            score += 0.1
        return min(score, 1.0)


# ---------------------------------------------------------------------------
# NERDetector (F-041)
# ---------------------------------------------------------------------------


class NERDetector(BaseDetector):
    """Enriches events with NER entity metadata via NEREngine.

    Wraps ``synapse.nlp.ner_engine.NEREngine``.
    Maps to ``EventType.SENTIMENT`` (metadata enrichment role).

    Input data keys:
        - ``text`` (str) or ``document`` (TextDocument): Chinese financial text.

    Always returns an Event if entities are found, enriching metadata
    with linked tickers and entity counts.
    """

    @classmethod
    def event_type(cls) -> str:
        return "ner_enrichment"

    def detect(self, data: dict) -> Optional[Event]:
        text = data.get("text", "")
        if not text:
            return None

        try:
            from synapse.nlp.ner_engine import NEREngine
            engine = NEREngine()
            doc = _text_to_doc(data)
            result = engine.recognize(doc)
        except Exception:
            logger.debug("NEREngine failed, degrading gracefully", exc_info=True)
            return None

        if not result.entities:
            return None

        confidence = self.confidence_score(data)
        tickers = _extract_tickers(data)

        # Collect linked tickers
        for entity in result.entities:
            if entity.linked_ticker and entity.linked_ticker not in tickers:
                tickers.append(entity.linked_ticker)

        # Summarize entities
        entity_counts: dict[str, int] = {}
        for entity in result.entities:
            entity_counts[entity.entity_type] = entity_counts.get(entity.entity_type, 0) + 1
        summary = ", ".join(f"{k}:{v}" for k, v in sorted(entity_counts.items()))

        return Event(
            id=_event_id(),
            event_type=EventType.SENTIMENT,
            title=f"NER: {summary}",
            description=(
                f"NER enrichment: {len(result.entities)} entities "
                f"({summary}), {len(tickers)} tickers linked"
            ),
            event_date=_extract_date(data),
            related_tickers=tickers,
            confidence=confidence,
            severity=0.3,
            source=EventSourceType.AI_DETECTED,
        )

    def confidence_score(self, data: dict, nlp_confidence: float = 0.0) -> float:
        """Score based on text presence."""
        text = data.get("text", "")
        if not text:
            return 0.0
        return min(0.4 + nlp_confidence * 0.6, 1.0)


# ---------------------------------------------------------------------------
# EventExtractionDetector (F-042)
# ---------------------------------------------------------------------------


class EventExtractionDetector(BaseDetector):
    """Detects structured events via EventExtractor.

    Wraps ``synapse.nlp.event_extractor.EventExtractor``.
    Maps extracted event types to P3 EventType strings.

    Input data keys:
        - ``text`` (str) or ``document`` (TextDocument): Chinese financial text.

    Returns the highest-confidence extracted event, or None.
    """

    # Map P3 event_type string to EventType enum
    _P3_TYPE_MAP: dict[str, EventType] = {
        "earnings": EventType.EARNINGS,
        "policy_change": EventType.POLICY_CHANGE,
        "corporate_action": EventType.CORPORATE_ACTION,
        "sentiment": EventType.SENTIMENT,
        "theme": EventType.THEME,
        "capital_flow": EventType.CAPITAL_FLOW,
        "macro_shift": EventType.MACRO_SHIFT,
        "social_sentiment": EventType.SOCIAL_SENTIMENT,
    }

    @classmethod
    def event_type(cls) -> str:
        return "event_extraction"

    def detect(self, data: dict) -> Optional[Event]:
        text = data.get("text", "")
        if not text:
            return None

        try:
            from synapse.nlp.event_extractor import EventExtractor
            extractor = EventExtractor()
            doc = _text_to_doc(data)
            result = extractor.extract(doc)
        except Exception:
            logger.debug("EventExtractor failed, degrading gracefully", exc_info=True)
            return None

        if not result.events:
            return None

        # Pick highest-confidence event
        best = max(result.events, key=lambda e: e.confidence)
        p3_type_str = EventExtractor.get_p3_event_type(best.event_type)
        event_type = self._P3_TYPE_MAP.get(p3_type_str, EventType.EARNINGS)

        confidence = self.confidence_score(data)
        tickers = _extract_tickers(data)

        return Event(
            id=_event_id(),
            event_type=event_type,
            title=f"Extracted: {best.event_type} ({best.trigger_phrase})",
            description=(
                f"Event extracted: {best.event_type}, "
                f"trigger='{best.trigger_phrase}', "
                f"participants={list(best.participants)[:3]}"
            ),
            event_date=best.date or _extract_date(data),
            related_tickers=tickers,
            confidence=confidence,
            severity=0.5,
            source=EventSourceType.AI_DETECTED,
        )

    def confidence_score(self, data: dict, nlp_confidence: float = 0.0) -> float:
        """Score based on text presence."""
        text = data.get("text", "")
        if not text:
            return 0.0
        return min(0.3 + nlp_confidence * 0.7, 1.0)
