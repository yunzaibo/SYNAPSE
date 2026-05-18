"""Integration test: end-to-end event detection -> impact -> graph pipeline."""

from __future__ import annotations

from pathlib import Path

import yaml
import pytest

from synapse.core.schemas.event import Event, EventType
from synapse.event.dedup import DeduplicationEngine
from synapse.event.detectors import EarningsDetector, PolicyDetector
from synapse.event.graph import PropagationGraph
from synapse.event.impact import ImpactAnalyzer
from synapse.event.registry import DetectorRegistry


def test_event_pipeline(tmp_path: Path) -> None:
    """End-to-end: create sample data -> detect -> dedup -> impact -> graph."""
    # 1. Create sample data files (fields match detector triggers)
    earnings_data = {
        "report_type": "Q3",
        "eps_surprise": 0.15,
        "tickers": ["600519"],
    }
    (tmp_path / "earnings_raw.yaml").write_text(yaml.dump(earnings_data))

    policy_data = {
        "source": "pboc.gov.cn",
        "policy_type": "rate_cut",
        "tickers": ["000001"],
    }
    (tmp_path / "policy_raw.yaml").write_text(yaml.dump(policy_data))

    # 2. Detection
    registry = DetectorRegistry()
    registry.register(EarningsDetector)
    registry.register(PolicyDetector)

    raw_earnings = yaml.safe_load(
        (tmp_path / "earnings_raw.yaml").read_text(encoding="utf-8")
    )
    earnings_events = registry.detect_all(raw_earnings)
    assert len(earnings_events) >= 1  # EarningsDetector should fire

    raw_policy = yaml.safe_load(
        (tmp_path / "policy_raw.yaml").read_text(encoding="utf-8")
    )
    policy_events = registry.detect_all(raw_policy)
    assert len(policy_events) >= 1  # PolicyDetector should fire

    # 3. Dedup
    dedup = DeduplicationEngine()
    key1 = dedup.compute_dedup_key(
        "earnings", "entity_001", "2026-01-01", "cninfo"
    )
    key2 = dedup.compute_dedup_key(
        "earnings", "entity_001", "2026-01-01", "news"
    )
    assert key1 != key2  # different sources = different keys

    # 4. Graph
    graph = PropagationGraph()
    graph.add_edge("evt_001", "thesis_001", weight=0.8)
    graph.add_edge("thesis_001", "pos_001", weight=0.7)
    graph.add_edge("evt_002", "thesis_002", weight=0.6)

    nodes = graph.get_all_nodes()
    assert len(nodes) == 5

    # 5. Impact
    event = Event(
        id="evt_001",
        event_type=EventType.EARNINGS,
        title="Q3 earnings",
        severity=0.8,
        confidence=0.9,
        decay_rate=0.1,
    )
    analyzer = ImpactAnalyzer(graph, event)
    report = analyzer.compute_full_report()
    assert report.event_id == "evt_001"
    assert report.total_impact > 0
