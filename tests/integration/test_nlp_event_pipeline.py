"""Integration tests for NLP-P3 Event Pipeline (F-043 / IMPL-008).

Tests end-to-end pipeline: NLP text -> NLP module -> detector -> Event ->
DetectorRegistry.detect_all() -> PropagationGraph -> ImpactAnalyzer.
"""

from __future__ import annotations

import pytest

from synapse.core.schemas.event import (
    Event,
    EventType,
    PropagationState,
)
from synapse.event.nlp_detectors import (
    AnnouncementDetector,
    ResearchReportDetector,
    NewsSentimentDetector,
    PolicyDetector_NLP,
    NERDetector,
    EventExtractionDetector,
)
from synapse.event.registry import DetectorRegistry
from synapse.event.graph import PropagationGraph
from synapse.event.impact import ImpactAnalyzer


# ---------------------------------------------------------------------------
# Sample texts
# ---------------------------------------------------------------------------

EARNINGS_TEXT = (
    "贵州茅台发布2024年第三季度业绩报告，净利润同比增长15.3%，"
    "营业收入达到869.2亿元，毛利率维持在91.5%的高水平。"
)

NEWS_TEXT = "茅台业绩大幅增长超预期，市场看好消费复苏前景。"

POLICY_TEXT = (
    "中国人民银行决定下调存款准备金率0.5个百分点，"
    "释放长期资金约1万亿元，支持实体经济发展。"
)

NER_TEXT = "贵州茅台酒股份有限公司董事长丁雄军表示，公司2024年营收目标为同比增长15%。"

EVENT_EXTRACT_TEXT = "贵州茅台预计2024年净利润增长15%，业绩预增公告发布。"

RESEARCH_REPORT_TEXT = (
    "贵州茅台深度研究报告\n"
    "评级：买入\n"
    "目标价：2100元\n"
    "投资要点：公司盈利能力持续提升，高端白酒需求稳健增长。\n"
    "风险提示：消费降级风险，行业竞争加剧。"
)


# ---------------------------------------------------------------------------
# Pipeline: NLP -> Detector -> Event
# ---------------------------------------------------------------------------


class TestNLPToDetectorPipeline:
    """Tests NLP text -> detector -> Event pipeline."""

    def test_earnings_pipeline(self):
        det = AnnouncementDetector()
        event = det.detect({"text": EARNINGS_TEXT})
        assert event is not None
        assert event.event_type == EventType.EARNINGS
        assert event.confidence > 0
        assert event.source.value == "news"

    def test_news_sentiment_pipeline(self):
        det = NewsSentimentDetector()
        event = det.detect({"text": NEWS_TEXT})
        assert event is not None
        assert event.event_type == EventType.SOCIAL_SENTIMENT

    def test_policy_pipeline(self):
        det = PolicyDetector_NLP()
        event = det.detect({"text": POLICY_TEXT})
        assert event is not None
        assert event.event_type == EventType.POLICY_CHANGE

    def test_ner_pipeline(self):
        det = NERDetector()
        event = det.detect({"text": NER_TEXT})
        assert event is not None
        assert event.source.value == "ai_detected"

    def test_event_extraction_pipeline(self):
        det = EventExtractionDetector()
        event = det.detect({"text": EVENT_EXTRACT_TEXT})
        assert event is not None
        assert "Extracted:" in event.title

    def test_research_report_pipeline(self):
        det = ResearchReportDetector()
        event = det.detect({"text": RESEARCH_REPORT_TEXT})
        assert event is not None
        assert event.event_type == EventType.SOCIAL_SENTIMENT


# ---------------------------------------------------------------------------
# Pipeline: DetectorRegistry.detect_all()
# ---------------------------------------------------------------------------


class TestRegistryDetectAll:
    """Tests DetectorRegistry.detect_all() with NLP detectors."""

    def _make_registry(self) -> DetectorRegistry:
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
        return registry

    def test_detect_all_earnings(self):
        registry = self._make_registry()
        events = registry.detect_all({"text": EARNINGS_TEXT})
        assert len(events) >= 1
        types = [e.event_type for e in events]
        assert EventType.EARNINGS in types

    def test_detect_all_news(self):
        registry = self._make_registry()
        events = registry.detect_all({"text": NEWS_TEXT})
        # Should find at least sentiment event
        assert len(events) >= 1

    def test_detect_all_policy(self):
        registry = self._make_registry()
        events = registry.detect_all({"text": POLICY_TEXT})
        types = [e.event_type for e in events]
        assert EventType.POLICY_CHANGE in types

    def test_detect_all_ner(self):
        registry = self._make_registry()
        events = registry.detect_all({"text": NER_TEXT})
        assert len(events) >= 1

    def test_detect_all_event_extraction(self):
        registry = self._make_registry()
        events = registry.detect_all({"text": EVENT_EXTRACT_TEXT})
        assert len(events) >= 1

    def test_detect_all_empty(self):
        registry = self._make_registry()
        events = registry.detect_all({"text": ""})
        assert events == []

    def test_detect_all_all_detectors_fire(self):
        """Multiple detectors can fire on the same text."""
        registry = self._make_registry()
        # Earnings text may trigger announcement + NER + event extraction
        events = registry.detect_all({"text": EARNINGS_TEXT})
        assert len(events) >= 2


# ---------------------------------------------------------------------------
# Pipeline: Event -> PropagationGraph
# ---------------------------------------------------------------------------


class TestNLPToGraphPipeline:
    """Tests NLP Event -> PropagationGraph flow."""

    def test_event_added_to_graph(self):
        det = AnnouncementDetector()
        event = det.detect({"text": EARNINGS_TEXT})
        assert event is not None

        graph = PropagationGraph()
        # Add event as node (using event.id as node_id)
        graph.add_edge(event.id, "thesis_1", weight=0.8)
        assert graph.has_node(event.id)
        assert "thesis_1" in graph.get_neighbors(event.id)

    def test_nlp_event_in_topological_sort(self):
        det = AnnouncementDetector()
        event = det.detect({"text": EARNINGS_TEXT})
        assert event is not None

        graph = PropagationGraph()
        graph.add_edge(event.id, "thesis_1", weight=0.7)
        graph.add_edge("thesis_1", "position_1", weight=0.5)

        topo = graph.topological_sort()
        assert event.id in topo
        assert topo.index(event.id) < topo.index("thesis_1")

    def test_multiple_nlp_events_in_graph(self):
        registry = DetectorRegistry()
        for cls in [
            AnnouncementDetector,
            NewsSentimentDetector,
            PolicyDetector_NLP,
            NERDetector,
            EventExtractionDetector,
        ]:
            registry.register(cls)

        events = registry.detect_all({"text": EARNINGS_TEXT})
        assert len(events) >= 1

        graph = PropagationGraph()
        for i, event in enumerate(events):
            graph.add_edge(event.id, f"thesis_{i}", weight=0.5)

        assert len(graph.get_all_nodes()) >= len(events) + 1


# ---------------------------------------------------------------------------
# Pipeline: Event -> ImpactAnalyzer
# ---------------------------------------------------------------------------


class TestNLPToImpactPipeline:
    """Tests NLP Event -> ImpactAnalyzer flow."""

    def test_impact_computed_for_nlp_event(self):
        det = AnnouncementDetector()
        event = det.detect({"text": EARNINGS_TEXT})
        assert event is not None

        graph = PropagationGraph()
        graph.add_edge(event.id, "thesis_1", weight=0.8)
        graph.add_edge("thesis_1", "position_A", weight=0.6)

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        direct = analyzer.compute_direct_impact()
        cascaded = analyzer.compute_cascaded_impact()

        assert "thesis_1" in direct
        assert "position_A" in cascaded
        assert direct["thesis_1"] > 0
        assert cascaded["position_A"] > 0

    def test_impact_uses_event_confidence(self):
        det = AnnouncementDetector()
        event = det.detect({"text": EARNINGS_TEXT})
        assert event is not None

        graph = PropagationGraph()
        graph.add_edge(event.id, "thesis_1", weight=1.0)

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        direct = analyzer.compute_direct_impact()

        # impact = severity * confidence * decay_factor * path_weight
        # With decay_rate=0.1, days=0, decay_factor=1.0
        expected = event.severity * event.confidence * 1.0 * 1.0
        assert abs(direct["thesis_1"] - expected) < 1e-6

    def test_full_report_for_nlp_event(self):
        det = AnnouncementDetector()
        event = det.detect({"text": EARNINGS_TEXT})
        assert event is not None

        graph = PropagationGraph()
        graph.add_edge(event.id, "thesis_1", weight=0.8)

        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        report = analyzer.compute_full_report()

        assert report.event_id == event.id
        assert report.total_impact > 0
        assert "thesis_1" in report.direct_impacts

    def test_impact_empty_graph(self):
        det = AnnouncementDetector()
        event = det.detect({"text": EARNINGS_TEXT})
        assert event is not None

        graph = PropagationGraph()
        analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
        direct = analyzer.compute_direct_impact()
        assert direct == {}


# ---------------------------------------------------------------------------
# End-to-end: Text -> Registry -> Graph -> Impact
# ---------------------------------------------------------------------------


class TestEndToEndPipeline:
    """Full end-to-end pipeline test."""

    def _make_registry(self) -> DetectorRegistry:
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
        return registry

    def test_full_pipeline_earnings(self):
        registry = self._make_registry()
        graph = PropagationGraph()

        # Step 1: Detect events from NLP text
        events = registry.detect_all({"text": EARNINGS_TEXT})
        assert len(events) >= 1

        # Step 2: Add events to propagation graph
        for event in events:
            graph.add_edge(event.id, "thesis_main", weight=0.7)
        graph.add_edge("thesis_main", "position茅台", weight=0.5)

        # Step 3: Compute impact for each event
        for event in events:
            analyzer = ImpactAnalyzer(graph, event, days_since_event=0.0)
            report = analyzer.compute_full_report()
            assert report.total_impact >= 0

        # Step 4: Verify graph integrity
        topo = graph.topological_sort()
        assert len(topo) >= len(events) + 2

    def test_full_pipeline_policy(self):
        registry = self._make_registry()
        graph = PropagationGraph()

        events = registry.detect_all({"text": POLICY_TEXT})
        assert len(events) >= 1

        for event in events:
            graph.add_edge(event.id, "sector_banking", weight=0.6)

        analyzer = ImpactAnalyzer(graph, events[0], days_since_event=0.0)
        direct = analyzer.compute_direct_impact()
        assert "sector_banking" in direct

    def test_full_pipeline_graceful_degradation(self):
        """Empty input -> no events -> no graph nodes -> no crashes."""
        registry = self._make_registry()
        events = registry.detect_all({"text": ""})
        assert events == []

        graph = PropagationGraph()
        assert graph.get_all_nodes() == []
