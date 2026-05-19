"""Tests for EventExtractor -- Chinese financial event extraction.

Covers: 5 event types (earnings forecast, M&A, equity change, policy change,
dividend), trigger phrase extraction with offsets, participant identification,
multi-event documents, edge cases, frozen dataclass behavior, round-trip
serialization.
"""

from __future__ import annotations

import pytest

from synapse.nlp.schemas import TextDocument, NEREntity, NERResult
from synapse.nlp.event_extractor import (
    EventExtractor,
    EventExtractionResult,
    ExtractedEvent,
)
from synapse.nlp.event_patterns import (
    ALL_TRIGGER_PATTERNS,
    EVENT_TYPE_TO_P3,
    EVENT_TYPE_KEYWORDS,
    EARNINGS_FORECAST,
    MERGER_ACQUISITION,
    EQUITY_CHANGE,
    POLICY_CHANGE,
    DIVIDEND,
    count_patterns,
    count_patterns_by_type,
)


# ---------------------------------------------------------------------------
# Frozen dataclass tests
# ---------------------------------------------------------------------------

class TestExtractedEventSchema:
    """Tests for ExtractedEvent frozen dataclass."""

    def test_frozen_and_slots(self) -> None:
        """ExtractedEvent must be frozen and use slots."""
        event = ExtractedEvent(event_type="EARNINGS_FORECAST", trigger_phrase="test")
        with pytest.raises(AttributeError):
            event.event_type = "changed"  # type: ignore[misc]

    def test_default_values(self) -> None:
        event = ExtractedEvent()
        assert event.event_type == ""
        assert event.trigger_phrase == ""
        assert event.participants == ()
        assert event.amount is None
        assert event.date is None
        assert event.confidence == 0.0
        assert event.entity_spans == ()

    def test_custom_values(self) -> None:
        from datetime import date
        event = ExtractedEvent(
            event_type="EARNINGS_FORECAST",
            trigger_phrase="预计净利润增长50%",
            participants=("贵州茅台",),
            amount=100000000.0,
            date=date(2026, 1, 1),
            confidence=0.85,
            entity_spans=((0, 4, "company"),),
        )
        assert event.event_type == "EARNINGS_FORECAST"
        assert event.participants == ("贵州茅台",)
        assert event.amount == 100000000.0

    def test_to_dict_roundtrip(self) -> None:
        from datetime import date
        event = ExtractedEvent(
            event_type="EARNINGS_FORECAST",
            trigger_phrase="预计增长",
            participants=("A公司", "B公司"),
            amount=50000.0,
            date=date(2026, 6, 1),
            confidence=0.9,
            entity_spans=((10, 14, "company"),),
        )
        d = event.to_dict()
        restored = ExtractedEvent.from_dict(d)
        assert restored == event

    def test_from_dict_none_amount(self) -> None:
        event = ExtractedEvent.from_dict({
            "event_type": "DIVIDEND",
            "trigger_phrase": "分红",
            "amount": None,
            "date": None,
        })
        assert event.amount is None
        assert event.date is None


class TestEventExtractionResultSchema:
    """Tests for EventExtractionResult frozen dataclass."""

    def test_frozen_and_slots(self) -> None:
        result = EventExtractionResult(events=(), processing_time_ms=1.0)
        with pytest.raises(AttributeError):
            result.events = ()  # type: ignore[misc]

    def test_to_dict_roundtrip(self) -> None:
        event = ExtractedEvent(
            event_type="MERGER_ACQUISITION",
            trigger_phrase="收购股权",
            confidence=0.88,
        )
        result = EventExtractionResult(
            events=(event,),
            processing_time_ms=12.5,
        )
        d = result.to_dict()
        restored = EventExtractionResult.from_dict(d)
        assert len(restored.events) == 1
        assert restored.events[0].event_type == "MERGER_ACQUISITION"
        assert restored.processing_time_ms == 12.5


# ---------------------------------------------------------------------------
# Event type constants
# ---------------------------------------------------------------------------

class TestEventTypes:
    """Verify 5 event types are defined correctly."""

    def test_five_event_types_exist(self) -> None:
        types = {EARNINGS_FORECAST, MERGER_ACQUISITION, EQUITY_CHANGE, POLICY_CHANGE, DIVIDEND}
        assert len(types) == 5

    def test_p3_mapping_exists(self) -> None:
        for et in [EARNINGS_FORECAST, MERGER_ACQUISITION, EQUITY_CHANGE, POLICY_CHANGE, DIVIDEND]:
            assert et in EVENT_TYPE_TO_P3

    def test_p3_mapping_values(self) -> None:
        assert EVENT_TYPE_TO_P3[EARNINGS_FORECAST] == "earnings"
        assert EVENT_TYPE_TO_P3[MERGER_ACQUISITION] == "corporate_action"
        assert EVENT_TYPE_TO_P3[EQUITY_CHANGE] == "corporate_action"
        assert EVENT_TYPE_TO_P3[POLICY_CHANGE] == "policy_change"
        assert EVENT_TYPE_TO_P3[DIVIDEND] == "corporate_action"


# ---------------------------------------------------------------------------
# Pattern count verification
# ---------------------------------------------------------------------------

class TestPatternCoverage:
    """Verify 30+ trigger patterns across 5 event types."""

    def test_total_pattern_count(self) -> None:
        assert count_patterns() >= 30

    def test_patterns_per_type(self) -> None:
        counts = count_patterns_by_type()
        assert counts[EARNINGS_FORECAST] >= 6
        assert counts[MERGER_ACQUISITION] >= 6
        assert counts[EQUITY_CHANGE] >= 6
        assert counts[POLICY_CHANGE] >= 5
        assert counts[DIVIDEND] >= 5

    def test_all_patterns_have_event_type(self) -> None:
        for pattern in ALL_TRIGGER_PATTERNS:
            assert pattern.event_type in EVENT_TYPE_TO_P3

    def test_keyword_coverage(self) -> None:
        for et in [EARNINGS_FORECAST, MERGER_ACQUISITION, EQUITY_CHANGE, POLICY_CHANGE, DIVIDEND]:
            assert et in EVENT_TYPE_KEYWORDS
            assert len(EVENT_TYPE_KEYWORDS[et]) >= 5


# ---------------------------------------------------------------------------
# Extraction tests: 5 event types
# ---------------------------------------------------------------------------

class TestEventExtraction:
    """Test extraction of each event type from Chinese text."""

    def setup_method(self) -> None:
        self.extractor = EventExtractor()

    def test_earnings_forecast_extraction(self) -> None:
        """Earnings forecast: '预计2026年净利润增长50%' should detect EARNINGS_FORECAST."""
        doc = TextDocument(
            text="公司预计2026年净利润增长50%，业绩预增明显。",
            doc_id="test-001",
        )
        result = self.extractor.extract(doc)

        assert len(result.events) >= 1
        event_types = [e.event_type for e in result.events]
        assert EARNINGS_FORECAST in event_types

        # Check trigger phrase is a non-empty substring of the text
        ef_event = next(e for e in result.events if e.event_type == EARNINGS_FORECAST)
        assert len(ef_event.trigger_phrase) > 0
        assert ef_event.trigger_phrase in doc.text
        assert ef_event.confidence > 0.0

    def test_ma_extraction(self) -> None:
        """M&A: '公司拟收购目标公司100%股权' should detect MERGER_ACQUISITION."""
        doc = TextDocument(
            text="公司拟收购目标公司100%股权，交易金额约5亿元。",
            doc_id="test-002",
        )
        result = self.extractor.extract(doc)

        assert len(result.events) >= 1
        event_types = [e.event_type for e in result.events]
        assert MERGER_ACQUISITION in event_types

        ma_event = next(e for e in result.events if e.event_type == MERGER_ACQUISITION)
        assert "收购" in ma_event.trigger_phrase

    def test_equity_change_extraction(self) -> None:
        """Equity change: '控股股东增持100万股' should detect EQUITY_CHANGE."""
        doc = TextDocument(
            text="控股股东增持100万股，增持金额约2000万元。",
            doc_id="test-003",
        )
        result = self.extractor.extract(doc)

        assert len(result.events) >= 1
        event_types = [e.event_type for e in result.events]
        assert EQUITY_CHANGE in event_types

        ec_event = next(e for e in result.events if e.event_type == EQUITY_CHANGE)
        assert "增持" in ec_event.trigger_phrase

    def test_policy_change_extraction(self) -> None:
        """Policy change: '证监会发布新规' should detect POLICY_CHANGE."""
        doc = TextDocument(
            text="证监会发布关于加强上市公司监管的通知，新规自2026年7月1日起施行。",
            doc_id="test-004",
        )
        result = self.extractor.extract(doc)

        assert len(result.events) >= 1
        event_types = [e.event_type for e in result.events]
        assert POLICY_CHANGE in event_types

    def test_dividend_extraction(self) -> None:
        """Dividend: '公司每10股派发现金红利5元' should detect DIVIDEND."""
        doc = TextDocument(
            text="公司2025年度分红方案：每10股派发现金红利5元（含税），送股0股，转增0股。",
            doc_id="test-005",
        )
        result = self.extractor.extract(doc)

        assert len(result.events) >= 1
        event_types = [e.event_type for e in result.events]
        assert DIVIDEND in event_types

        div_event = next(e for e in result.events if e.event_type == DIVIDEND)
        assert div_event.confidence > 0.0


# ---------------------------------------------------------------------------
# Trigger phrase offset tests
# ---------------------------------------------------------------------------

class TestTriggerPhraseOffsets:
    """Verify trigger phrases are substrings of the original text."""

    def setup_method(self) -> None:
        self.extractor = EventExtractor()

    def test_trigger_phrase_is_substring(self) -> None:
        doc = TextDocument(
            text="公司预计2026年净利润增长50%，业绩预增明显。",
            doc_id="test-offset-001",
        )
        result = self.extractor.extract(doc)

        for event in result.events:
            assert event.trigger_phrase in doc.text, (
                f"Trigger phrase '{event.trigger_phrase}' not found in text"
            )

    def test_entity_spans_are_valid(self) -> None:
        doc = TextDocument(
            text="贵州茅台预计2026年净利润增长50%，业绩预增明显。",
            doc_id="test-offset-002",
        )
        result = self.extractor.extract(doc)

        for event in result.events:
            for start, end, etype in event.entity_spans:
                assert 0 <= start < end <= len(doc.text), (
                    f"Invalid entity span ({start}, {end}) for text length {len(doc.text)}"
                )


# ---------------------------------------------------------------------------
# Multi-event document test
# ---------------------------------------------------------------------------

class TestMultiEventDocument:
    """Test documents containing multiple event types."""

    def setup_method(self) -> None:
        self.extractor = EventExtractor()

    def test_multi_event_document(self) -> None:
        """Document with earnings forecast + dividend should yield 2+ events."""
        doc = TextDocument(
            text="贵州茅台预计2026年净利润增长30%，同时公布年度分红方案，每10股派发现金红利30元。",
            doc_id="test-multi-001",
        )
        result = self.extractor.extract(doc)

        assert len(result.events) >= 2
        event_types = {e.event_type for e in result.events}
        assert EARNINGS_FORECAST in event_types
        assert DIVIDEND in event_types

    def test_ma_plus_equity_change(self) -> None:
        """Document with M&A + equity change."""
        doc = TextDocument(
            text="公司拟收购目标公司100%股权，同时控股股东减持500万股。",
            doc_id="test-multi-002",
        )
        result = self.extractor.extract(doc)

        assert len(result.events) >= 2
        event_types = {e.event_type for e in result.events}
        assert MERGER_ACQUISITION in event_types
        assert EQUITY_CHANGE in event_types


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge case tests."""

    def setup_method(self) -> None:
        self.extractor = EventExtractor()

    def test_empty_text(self) -> None:
        doc = TextDocument(text="", doc_id="test-edge-001")
        result = self.extractor.extract(doc)
        assert result.events == ()
        assert result.processing_time_ms >= 0.0

    def test_no_event_text(self) -> None:
        doc = TextDocument(
            text="今天天气不错，适合出去走走。",
            doc_id="test-edge-002",
        )
        result = self.extractor.extract(doc)
        assert len(result.events) == 0

    def test_single_keyword_text(self) -> None:
        """Text with just one keyword should still produce an event via fallback."""
        doc = TextDocument(
            text="公司发布了新的分红方案。",
            doc_id="test-edge-003",
        )
        result = self.extractor.extract(doc)
        # Should detect at least one event via keyword or pattern
        assert len(result.events) >= 1

    def test_processing_time_is_non_negative(self) -> None:
        doc = TextDocument(text="测试文本", doc_id="test-edge-004")
        result = self.extractor.extract(doc)
        assert result.processing_time_ms >= 0.0


# ---------------------------------------------------------------------------
# P3 EventType mapping
# ---------------------------------------------------------------------------

class TestP3Mapping:
    """Test P3 EventType string mapping."""

    def test_get_p3_earnings(self) -> None:
        assert EventExtractor.get_p3_event_type("EARNINGS_FORECAST") == "earnings"

    def test_get_p3_ma(self) -> None:
        assert EventExtractor.get_p3_event_type("MERGER_ACQUISITION") == "corporate_action"

    def test_get_p3_equity(self) -> None:
        assert EventExtractor.get_p3_event_type("EQUITY_CHANGE") == "corporate_action"

    def test_get_p3_policy(self) -> None:
        assert EventExtractor.get_p3_event_type("POLICY_CHANGE") == "policy_change"

    def test_get_p3_dividend(self) -> None:
        assert EventExtractor.get_p3_event_type("DIVIDEND") == "corporate_action"

    def test_get_p3_unknown_defaults_to_earnings(self) -> None:
        assert EventExtractor.get_p3_event_type("UNKNOWN_TYPE") == "earnings"
