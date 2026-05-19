"""Unit tests for NLP Detectors (F-043 / IMPL-008).

Tests all 6 NLP BaseDetector implementations:
- AnnouncementDetector
- ResearchReportDetector
- NewsSentimentDetector
- PolicyDetector_NLP
- NERDetector
- EventExtractionDetector

Covers: detect(), event_type(), confidence_score(), graceful degradation,
Event schema compliance, and confidence propagation.
"""

from __future__ import annotations

import pytest

from synapse.core.schemas.event import (
    Event,
    EventType,
    EventSourceType,
)
from synapse.event.nlp_detectors import (
    AnnouncementDetector,
    ResearchReportDetector,
    NewsSentimentDetector,
    PolicyDetector_NLP,
    NERDetector,
    EventExtractionDetector,
    _text_to_doc,
)
from synapse.event.registry import DetectorRegistry
from synapse.nlp.schemas import TextDocument


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ANNOUNCEMENT_TEXT = (
    "贵州茅台发布2024年第三季度业绩报告，净利润同比增长15.3%，"
    "营业收入达到869.2亿元，毛利率维持在91.5%的高水平。"
)

RESEARCH_REPORT_TEXT = (
    "贵州茅台深度研究报告\n"
    "评级：买入\n"
    "目标价：2100元\n"
    "投资要点：公司盈利能力持续提升，高端白酒需求稳健增长。\n"
    "风险提示：消费降级风险，行业竞争加剧。"
)

BULLISH_NEWS_TEXT = "茅台业绩大幅增长超预期，市场看好消费复苏前景。"

BEARISH_NEWS_TEXT = "茅台股价暴跌，业绩大幅下滑，亏损严重。"

POLICY_TEXT = (
    "中国人民银行决定下调存款准备金率0.5个百分点，"
    "释放长期资金约1万亿元，支持实体经济发展。"
)

NER_TEXT = "贵州茅台酒股份有限公司董事长丁雄军表示，公司2024年营收目标为同比增长15%。"

EVENT_EXTRACT_TEXT = "贵州茅台预计2024年净利润增长15%，业绩预增公告发布。"


# ---------------------------------------------------------------------------
# AnnouncementDetector tests
# ---------------------------------------------------------------------------


class TestAnnouncementDetector:
    """Tests for AnnouncementDetector."""

    def test_event_type(self):
        assert AnnouncementDetector.event_type() == "earnings"

    def test_detect_returns_event(self):
        det = AnnouncementDetector()
        event = det.detect({"text": ANNOUNCEMENT_TEXT})
        assert event is not None
        assert isinstance(event, Event)
        assert event.event_type == EventType.EARNINGS
        assert "Announcement:" in event.title
        assert event.source == EventSourceType.NEWS

    def test_detect_empty_text_returns_none(self):
        det = AnnouncementDetector()
        assert det.detect({"text": ""}) is None
        assert det.detect({}) is None

    def test_detect_no_metrics_returns_none(self):
        det = AnnouncementDetector()
        # Plain text with no financial metrics
        assert det.detect({"text": "hello world"}) is None

    def test_confidence_in_valid_range(self):
        det = AnnouncementDetector()
        score = det.confidence_score({"text": ANNOUNCEMENT_TEXT})
        assert 0.0 <= score <= 1.0

    def test_confidence_empty_text(self):
        det = AnnouncementDetector()
        assert det.confidence_score({"text": ""}) == 0.0

    def test_detect_graceful_degradation(self):
        """If NLP module fails, detect() returns None instead of crashing."""
        det = AnnouncementDetector()
        # Pass invalid document type to trigger error path
        event = det.detect({"text": ANNOUNCEMENT_TEXT, "document": "invalid"})
        # Should either return Event (if text fallback works) or None (graceful)
        assert event is None or isinstance(event, Event)

    def test_event_schema_compliance(self):
        det = AnnouncementDetector()
        event = det.detect({"text": ANNOUNCEMENT_TEXT})
        if event is not None:
            assert event.id  # non-empty
            assert 0.0 <= event.confidence <= 1.0
            assert 0.0 <= event.severity <= 1.0
            assert isinstance(event.event_type, EventType)


# ---------------------------------------------------------------------------
# ResearchReportDetector tests
# ---------------------------------------------------------------------------


class TestResearchReportDetector:
    """Tests for ResearchReportDetector."""

    def test_event_type(self):
        assert ResearchReportDetector.event_type() == "research_sentiment"

    def test_detect_returns_event(self):
        det = ResearchReportDetector()
        event = det.detect({"text": RESEARCH_REPORT_TEXT})
        assert event is not None
        assert isinstance(event, Event)
        assert event.event_type == EventType.SOCIAL_SENTIMENT

    def test_detect_empty_text_returns_none(self):
        det = ResearchReportDetector()
        assert det.detect({"text": ""}) is None
        assert det.detect({}) is None

    def test_detect_no_report_returns_none(self):
        det = ResearchReportDetector()
        assert det.detect({"text": "random text without report structure"}) is None

    def test_confidence_in_valid_range(self):
        det = ResearchReportDetector()
        score = det.confidence_score({"text": RESEARCH_REPORT_TEXT})
        assert 0.0 <= score <= 1.0

    def test_confidence_empty_text(self):
        det = ResearchReportDetector()
        assert det.confidence_score({"text": ""}) == 0.0

    def test_detect_graceful_degradation(self):
        det = ResearchReportDetector()
        event = det.detect({"text": RESEARCH_REPORT_TEXT, "document": "invalid"})
        assert event is None or isinstance(event, Event)


# ---------------------------------------------------------------------------
# NewsSentimentDetector tests
# ---------------------------------------------------------------------------


class TestNewsSentimentDetector:
    """Tests for NewsSentimentDetector."""

    def test_event_type(self):
        assert NewsSentimentDetector.event_type() == "social_sentiment"

    def test_detect_bullish(self):
        det = NewsSentimentDetector()
        event = det.detect({"text": BULLISH_NEWS_TEXT})
        assert event is not None
        assert isinstance(event, Event)
        assert event.event_type == EventType.SOCIAL_SENTIMENT
        assert "bullish" in event.title.lower() or "Sentiment:" in event.title

    def test_detect_bearish(self):
        det = NewsSentimentDetector()
        event = det.detect({"text": BEARISH_NEWS_TEXT})
        assert event is not None
        assert isinstance(event, Event)
        assert "bearish" in event.title.lower() or "Sentiment:" in event.title

    def test_detect_neutral_returns_none(self):
        det = NewsSentimentDetector()
        # Neutral text should not fire
        event = det.detect({"text": "今天天气不错"})
        assert event is None

    def test_detect_empty_text_returns_none(self):
        det = NewsSentimentDetector()
        assert det.detect({"text": ""}) is None
        assert det.detect({}) is None

    def test_confidence_in_valid_range(self):
        det = NewsSentimentDetector()
        score = det.confidence_score({"text": BULLISH_NEWS_TEXT})
        assert 0.0 <= score <= 1.0

    def test_confidence_empty_text(self):
        det = NewsSentimentDetector()
        assert det.confidence_score({"text": ""}) == 0.0

    def test_detect_graceful_degradation(self):
        det = NewsSentimentDetector()
        event = det.detect({"text": BULLISH_NEWS_TEXT, "document": "invalid"})
        assert event is None or isinstance(event, Event)


# ---------------------------------------------------------------------------
# PolicyDetector_NLP tests
# ---------------------------------------------------------------------------


class TestPolicyDetectorNLP:
    """Tests for PolicyDetector_NLP."""

    def test_event_type(self):
        assert PolicyDetector_NLP.event_type() == "policy_change"

    def test_detect_returns_event(self):
        det = PolicyDetector_NLP()
        event = det.detect({"text": POLICY_TEXT})
        assert event is not None
        assert isinstance(event, Event)
        assert event.event_type == EventType.POLICY_CHANGE
        assert "Policy:" in event.title

    def test_detect_empty_text_returns_none(self):
        det = PolicyDetector_NLP()
        assert det.detect({"text": ""}) is None
        assert det.detect({}) is None

    def test_detect_no_policy_returns_none(self):
        det = PolicyDetector_NLP()
        assert det.detect({"text": "今天天气很好，适合出去玩。"}) is None

    def test_confidence_in_valid_range(self):
        det = PolicyDetector_NLP()
        score = det.confidence_score({"text": POLICY_TEXT})
        assert 0.0 <= score <= 1.0

    def test_confidence_boosts_for_official_source(self):
        det = PolicyDetector_NLP()
        # Text with explicit abbreviation "央行" triggers official source boost
        text_with_abbreviation = "央行决定下调存款准备金率0.5个百分点。"
        score = det.confidence_score({"text": text_with_abbreviation})
        assert score > 0.3

    def test_confidence_empty_text(self):
        det = PolicyDetector_NLP()
        assert det.confidence_score({"text": ""}) == 0.0

    def test_detect_graceful_degradation(self):
        det = PolicyDetector_NLP()
        event = det.detect({"text": POLICY_TEXT, "document": "invalid"})
        assert event is None or isinstance(event, Event)


# ---------------------------------------------------------------------------
# NERDetector tests
# ---------------------------------------------------------------------------


class TestNERDetector:
    """Tests for NERDetector."""

    def test_event_type(self):
        assert NERDetector.event_type() == "ner_enrichment"

    def test_detect_returns_event(self):
        det = NERDetector()
        event = det.detect({"text": NER_TEXT})
        assert event is not None
        assert isinstance(event, Event)
        assert event.source == EventSourceType.AI_DETECTED
        assert "NER:" in event.title

    def test_detect_empty_text_returns_none(self):
        det = NERDetector()
        assert det.detect({"text": ""}) is None
        assert det.detect({}) is None

    def test_detect_no_entities_returns_none(self):
        det = NERDetector()
        # Very short text may have no entities
        assert det.detect({"text": "a"}) is None

    def test_confidence_in_valid_range(self):
        det = NERDetector()
        score = det.confidence_score({"text": NER_TEXT})
        assert 0.0 <= score <= 1.0

    def test_confidence_empty_text(self):
        det = NERDetector()
        assert det.confidence_score({"text": ""}) == 0.0

    def test_detect_graceful_degradation(self):
        det = NERDetector()
        event = det.detect({"text": NER_TEXT, "document": "invalid"})
        assert event is None or isinstance(event, Event)

    def test_event_schema_compliance(self):
        det = NERDetector()
        event = det.detect({"text": NER_TEXT})
        if event is not None:
            assert event.id
            assert 0.0 <= event.confidence <= 1.0
            assert 0.0 <= event.severity <= 1.0


# ---------------------------------------------------------------------------
# EventExtractionDetector tests
# ---------------------------------------------------------------------------


class TestEventExtractionDetector:
    """Tests for EventExtractionDetector."""

    def test_event_type(self):
        assert EventExtractionDetector.event_type() == "event_extraction"

    def test_detect_returns_event(self):
        det = EventExtractionDetector()
        event = det.detect({"text": EVENT_EXTRACT_TEXT})
        assert event is not None
        assert isinstance(event, Event)
        assert "Extracted:" in event.title
        assert event.source == EventSourceType.AI_DETECTED

    def test_detect_empty_text_returns_none(self):
        det = EventExtractionDetector()
        assert det.detect({"text": ""}) is None
        assert det.detect({}) is None

    def test_detect_no_events_returns_none(self):
        det = EventExtractionDetector()
        assert det.detect({"text": "hello world"}) is None

    def test_confidence_in_valid_range(self):
        det = EventExtractionDetector()
        score = det.confidence_score({"text": EVENT_EXTRACT_TEXT})
        assert 0.0 <= score <= 1.0

    def test_confidence_empty_text(self):
        det = EventExtractionDetector()
        assert det.confidence_score({"text": ""}) == 0.0

    def test_detect_graceful_degradation(self):
        det = EventExtractionDetector()
        event = det.detect({"text": EVENT_EXTRACT_TEXT, "document": "invalid"})
        assert event is None or isinstance(event, Event)


# ---------------------------------------------------------------------------
# Registry integration tests
# ---------------------------------------------------------------------------


class TestNLPDetectorRegistry:
    """Tests for NLP detector registration."""

    def test_all_6_register(self):
        registry = DetectorRegistry()
        for cls in [
            AnnouncementDetector,
            ResearchReportDetector,
            NewsSentimentDetector,
            PolicyDetector_NLP,
            NERDetector,
            EventExtractionDetector,
        ]:
            registry.register(cls)
        assert len(registry.list_detectors()) == 6

    def test_registry_keys(self):
        registry = DetectorRegistry()
        for cls in [
            AnnouncementDetector,
            ResearchReportDetector,
            NewsSentimentDetector,
            PolicyDetector_NLP,
            NERDetector,
            EventExtractionDetector,
        ]:
            registry.register(cls)
        keys = set(registry.list_detectors().keys())
        expected = {
            "earnings", "research_sentiment", "social_sentiment",
            "policy_change", "ner_enrichment", "event_extraction",
        }
        assert keys == expected

    def test_detect_all_with_text(self):
        registry = DetectorRegistry()
        for cls in [
            AnnouncementDetector,
            ResearchReportDetector,
            NewsSentimentDetector,
            PolicyDetector_NLP,
            NERDetector,
            EventExtractionDetector,
        ]:
            registry.register(cls)
        events = registry.detect_all({"text": ANNOUNCEMENT_TEXT})
        # At least announcement detector should fire
        assert len(events) >= 1
        assert all(isinstance(e, Event) for e in events)


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestTextToDoc:
    """Tests for _text_to_doc helper."""

    def test_string_text(self):
        doc = _text_to_doc({"text": "hello"})
        assert isinstance(doc, TextDocument)
        assert doc.text == "hello"

    def test_document_passthrough(self):
        original = TextDocument(text="hello", doc_id="test")
        doc = _text_to_doc({"document": original})
        assert doc is original

    def test_empty(self):
        doc = _text_to_doc({})
        assert isinstance(doc, TextDocument)
        assert doc.text == ""


# ---------------------------------------------------------------------------
# Confidence propagation tests
# ---------------------------------------------------------------------------


class TestConfidencePropagation:
    """Tests that confidence scores propagate correctly."""

    def test_announcement_confidence_propagates(self):
        det = AnnouncementDetector()
        event = det.detect({"text": ANNOUNCEMENT_TEXT})
        if event is not None:
            # detect() passes nlp_confidence internally; verify event.confidence
            # is in valid range and consistent
            assert 0.0 <= event.confidence <= 1.0
            # The score should be > base (0.3) since NLP found data
            assert event.confidence > 0.3

    def test_policy_confidence_propagates(self):
        det = PolicyDetector_NLP()
        event = det.detect({"text": POLICY_TEXT})
        if event is not None:
            assert 0.0 <= event.confidence <= 1.0
            assert event.confidence >= 0.3

    def test_sentiment_confidence_propagates(self):
        det = NewsSentimentDetector()
        event = det.detect({"text": BULLISH_NEWS_TEXT})
        if event is not None:
            assert 0.0 <= event.confidence <= 1.0
            assert event.confidence > 0.3

    def test_ner_confidence_propagates(self):
        det = NERDetector()
        event = det.detect({"text": NER_TEXT})
        if event is not None:
            assert 0.0 <= event.confidence <= 1.0
            assert event.confidence > 0.3

    def test_event_extraction_confidence_propagates(self):
        det = EventExtractionDetector()
        event = det.detect({"text": EVENT_EXTRACT_TEXT})
        if event is not None:
            assert 0.0 <= event.confidence <= 1.0
            assert event.confidence >= 0.3

    def test_research_report_confidence_propagates(self):
        det = ResearchReportDetector()
        event = det.detect({"text": RESEARCH_REPORT_TEXT})
        if event is not None:
            assert 0.0 <= event.confidence <= 1.0
            assert event.confidence >= 0.2
