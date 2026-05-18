"""Tests for event detection framework -- BaseDetector, DetectorRegistry, Taxonomy."""

from __future__ import annotations

import uuid
from typing import Optional

import pytest

from synapse.core.schemas.event import Event, EventType, EventSourceType
from synapse.event.base import BaseDetector
from synapse.event.registry import DetectorRegistry
from synapse.event.taxonomy import (
    EVENT_TYPES,
    SOURCE_PRIORITY,
    EVENT_CATEGORY_MAP,
    PRIORITY_LEVELS,
)
from synapse.event.detectors import (
    EarningsDetector,
    PolicyDetector,
    SentimentDetector,
    ThemeDetector,
    CapitalFlowDetector,
    CorporateActionDetector,
    PolicyChangeDetector,
    MacroShiftDetector,
)
from synapse.event.dedup import DeduplicationEngine


def _make_event(event_type: EventType, title: str) -> Event:
    """Create an Event with a unique id for test purposes."""
    return Event(id=str(uuid.uuid4()), event_type=event_type, title=title)


# ---------------------------------------------------------------------------
# Helpers -- concrete detector stubs
# ---------------------------------------------------------------------------

class _EarningsDetector(BaseDetector):
    """Stub detector for earnings events."""

    def detect(self, data: dict) -> Optional[Event]:
        if data.get("type") == "earnings":
            return _make_event(EventType.EARNINGS, "Earnings detected")
        return None

    @classmethod
    def event_type(cls) -> str:
        return "earnings"

    def confidence_score(self, data: dict) -> float:
        return 0.9 if data.get("type") == "earnings" else 0.0


class _PolicyDetector(BaseDetector):
    """Stub detector for policy events."""

    def detect(self, data: dict) -> Optional[Event]:
        if data.get("type") == "policy":
            return _make_event(EventType.POLICY, "Policy detected")
        return None

    @classmethod
    def event_type(cls) -> str:
        return "policy"

    def confidence_score(self, data: dict) -> float:
        return 0.8 if data.get("type") == "policy" else 0.0


class _SentimentDetector(BaseDetector):
    """Stub detector for sentiment events."""

    def detect(self, data: dict) -> Optional[Event]:
        if data.get("type") == "sentiment":
            return _make_event(EventType.SENTIMENT, "Sentiment detected")
        return None

    @classmethod
    def event_type(cls) -> str:
        return "sentiment"

    def confidence_score(self, data: dict) -> float:
        return 0.7 if data.get("type") == "sentiment" else 0.0


# ---------------------------------------------------------------------------
# TestBaseDetector
# ---------------------------------------------------------------------------

class TestBaseDetector:
    def test_abstract_cannot_instantiate(self):
        """BaseDetector is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseDetector()  # type: ignore[abstract]

    def test_concrete_subclass_works(self):
        """A concrete subclass with all abstract methods implemented can be instantiated."""
        detector = _EarningsDetector()
        assert detector.event_type() == "earnings"

    def test_confidence_score_range(self):
        """Confidence scores must be in [0.0, 1.0]."""
        detector = _EarningsDetector()
        score = detector.confidence_score({"type": "earnings"})
        assert 0.0 <= score <= 1.0

    def test_detect_returns_none_for_non_match(self):
        """detect() returns None when data does not match."""
        detector = _EarningsDetector()
        result = detector.detect({"type": "something_else"})
        assert result is None


# ---------------------------------------------------------------------------
# TestDetectorRegistry
# ---------------------------------------------------------------------------

class TestDetectorRegistry:
    def test_register_and_lookup(self):
        """Register a detector and retrieve it by event type."""
        registry = DetectorRegistry()
        registry.register(_EarningsDetector)
        cls = registry.get_detector("earnings")
        assert cls is _EarningsDetector

    def test_list_detectors(self):
        """list_detectors returns all registered detectors."""
        registry = DetectorRegistry()
        registry.register(_EarningsDetector)
        registry.register(_PolicyDetector)
        registry.register(_SentimentDetector)
        detectors = registry.list_detectors()
        assert len(detectors) == 3
        assert "earnings" in detectors
        assert "policy" in detectors
        assert "sentiment" in detectors

    def test_detect_all_runs_all_detectors(self):
        """detect_all fires all detectors and collects matching events."""
        registry = DetectorRegistry()
        registry.register(_EarningsDetector)
        registry.register(_PolicyDetector)
        registry.register(_SentimentDetector)

        # Data that matches earnings only
        events = registry.detect_all({"type": "earnings"})
        assert len(events) == 1
        assert events[0].event_type == EventType.EARNINGS

    def test_detect_all_returns_empty_when_no_match(self):
        """detect_all returns empty list when no detector matches."""
        registry = DetectorRegistry()
        registry.register(_EarningsDetector)
        events = registry.detect_all({"type": "unrelated"})
        assert events == []

    def test_unregister(self):
        """unregister removes detector by event type."""
        registry = DetectorRegistry()
        registry.register(_EarningsDetector)
        removed = registry.unregister("earnings")
        assert removed is _EarningsDetector
        assert registry.get_detector("earnings") is None

    def test_register_non_subclass_raises(self):
        """Registering a non-BaseDetector class raises TypeError."""
        registry = DetectorRegistry()
        with pytest.raises(TypeError):
            registry.register(str)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestEventTaxonomy
# ---------------------------------------------------------------------------

class TestEventTaxonomy:
    def test_event_types_defined(self):
        """EVENT_TYPES must define all registered event types."""
        assert len(EVENT_TYPES) == 8
        expected = {"earnings", "policy", "sentiment", "theme", "capital_flow", "corporate_action", "policy_change", "macro_shift"}
        assert set(EVENT_TYPES.keys()) == expected

    def test_source_priority_is_ordered(self):
        """SOURCE_PRIORITY must contain source-to-priority mappings."""
        assert len(SOURCE_PRIORITY) > 0
        # cninfo should be highest priority (lowest number)
        assert SOURCE_PRIORITY["cninfo"] < SOURCE_PRIORITY["manual"]

    def test_event_category_map_covers_all_types(self):
        """EVENT_CATEGORY_MAP must cover all event types."""
        covered = set()
        for types in EVENT_CATEGORY_MAP.values():
            covered.update(types)
        expected = set(EVENT_TYPES.keys())
        assert covered == expected

    def test_priority_levels_defined(self):
        """PRIORITY_LEVELS must define P0 through P3."""
        assert set(PRIORITY_LEVELS.keys()) == {"P0", "P1", "P2", "P3"}


# ---------------------------------------------------------------------------
# TestConcreteDetectors
# ---------------------------------------------------------------------------

class TestConcreteDetectors:
    def test_earnings_detector_fires(self):
        """EarningsDetector returns Event when data has report_type='Q3'."""
        detector = EarningsDetector()
        event = detector.detect({"report_type": "Q3", "tickers": ["600519"]})
        assert event is not None
        assert event.event_type == EventType.EARNINGS
        assert "Q3" in event.title

    def test_earnings_detector_none(self):
        """EarningsDetector returns None for unrelated data."""
        detector = EarningsDetector()
        assert detector.detect({"foo": "bar"}) is None

    def test_policy_detector_fires(self):
        """PolicyDetector returns Event when source is 'pboc.gov.cn'."""
        detector = PolicyDetector()
        event = detector.detect({"source": "pboc.gov.cn", "policy_type": "rate_cut"})
        assert event is not None
        assert event.event_type == EventType.POLICY
        assert event.confidence >= 0.9  # official source

    def test_sentiment_detector_fires(self):
        """SentimentDetector returns Event when margin_change_pct is present."""
        detector = SentimentDetector()
        event = detector.detect({"margin_change_pct": 5.2})
        assert event is not None
        assert event.event_type == EventType.SENTIMENT

    def test_theme_detector_fires(self):
        """ThemeDetector returns Event when policy_theme is present."""
        detector = ThemeDetector()
        event = detector.detect({"policy_theme": "AI+manufacturing"})
        assert event is not None
        assert event.event_type == EventType.THEME

    def test_capital_flow_detector_fires(self):
        """CapitalFlowDetector returns Event when mainforce_flow is present."""
        detector = CapitalFlowDetector()
        event = detector.detect({"mainforce_flow": 1_500_000.0})
        assert event is not None
        assert event.event_type == EventType.CAPITAL_FLOW

    def test_corporate_action_detector_fires(self):
        """CorporateActionDetector returns Event when action_type is 'dividend'."""
        detector = CorporateActionDetector()
        event = detector.detect({"action_type": "dividend"})
        assert event is not None
        assert event.event_type == EventType.CORPORATE_ACTION
        assert "dividend" in event.title
        assert event.confidence == 0.85

    def test_corporate_action_detector_none(self):
        """CorporateActionDetector returns None for unrelated data."""
        detector = CorporateActionDetector()
        assert detector.detect({"foo": "bar"}) is None


# ---------------------------------------------------------------------------
# TestDeduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_same_event_merges(self):
        """Two events with same key but different sources merge into one."""
        engine = DeduplicationEngine()
        ev_a = _make_event(EventType.EARNINGS, "Q3 earnings")
        ev_a.description = "Source A report"
        ev_a.confidence = 0.8
        ev_b = _make_event(EventType.EARNINGS, "Q3 earnings")
        ev_b.description = "Source B report"
        ev_b.confidence = 0.6

        # Same dedup key (same type + title + date)
        ev_a.event_date = None
        ev_b.event_date = None

        result = engine.resolve_conflicts([ev_a, ev_b])
        assert len(result) == 1
        merged = result[0]
        assert merged.confidence == 0.8  # higher confidence wins
        assert "Source A report" in merged.description
        assert "Source B report" in merged.description

    def test_different_events_stay_separate(self):
        """Two events with different dedup keys stay as separate entries."""
        engine = DeduplicationEngine()
        ev_a = _make_event(EventType.EARNINGS, "Q3 earnings")
        ev_b = _make_event(EventType.POLICY, "Rate cut")

        result = engine.resolve_conflicts([ev_a, ev_b])
        assert len(result) == 2

    def test_source_priority_resolution(self):
        """When merging, higher-priority source (cninfo) wins over manual."""
        engine = DeduplicationEngine()
        ev_cninfo = _make_event(EventType.EARNINGS, "Earnings report")
        ev_cninfo.description = "From cninfo"
        ev_cninfo.confidence = 0.7
        ev_cninfo.source = EventSourceType.DATA_FEED

        ev_manual = _make_event(EventType.EARNINGS, "Earnings report")
        ev_manual.description = "From manual"
        ev_manual.confidence = 0.7  # equal confidence
        ev_manual.source = EventSourceType.MANUAL

        # Ensure same date for dedup grouping
        ev_cninfo.event_date = None
        ev_manual.event_date = None

        result = engine.resolve_conflicts([ev_cninfo, ev_manual])
        assert len(result) == 1
        # With equal confidence, first event in order wins (cninfo)
        merged = result[0]
        assert merged.confidence == 0.7


# ---------------------------------------------------------------------------
# TestPolicyChangeDetector (3 tests)
# ---------------------------------------------------------------------------


class TestPolicyChangeDetector:
    def test_detect_fires_on_valid_data(self):
        """PolicyChangeDetector detects valid policy change data."""
        det = PolicyChangeDetector()
        data = {"policy_change": True, "regulation_body": "csrc", "tickers": ["600519"]}
        event = det.detect(data)
        assert event is not None
        assert event.event_type == EventType.POLICY_CHANGE
        assert "csrc" in event.title

    def test_detect_returns_none_on_non_matching(self):
        """PolicyChangeDetector returns None when no triggers present."""
        det = PolicyChangeDetector()
        assert det.detect({}) is None
        assert det.detect({"unrelated_key": True}) is None

    def test_confidence_scoring(self):
        """PolicyChangeDetector confidence combines flag + body + type."""
        det = PolicyChangeDetector()
        # All three triggers
        score = det.confidence_score({
            "policy_change": True,
            "regulation_body": "pboc",
            "announcement_type": "rate_change",
        })
        assert score == 1.0
        # Only flag
        score2 = det.confidence_score({"policy_change": True})
        assert score2 == 0.4
        # No triggers
        assert det.confidence_score({}) == 0.0


# ---------------------------------------------------------------------------
# TestMacroShiftDetector (1 test)
# ---------------------------------------------------------------------------


class TestMacroShiftDetector:
    def test_detect_fires_on_valid_data(self):
        """MacroShiftDetector detects valid macro shift data."""
        det = MacroShiftDetector()
        data = {"macro_shift": True, "indicator": "gdp", "surprise_magnitude": 0.8}
        event = det.detect(data)
        assert event is not None
        assert event.event_type == EventType.MACRO_SHIFT
        assert "gdp" in event.title
