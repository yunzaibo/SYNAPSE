"""SYNAPSE Event -- Pluggable event detection framework with propagation graph.

Provides BaseDetector ABC, DetectorRegistry, and event taxonomy constants
for A-share market event types, plus DAG-based event propagation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from synapse.event.graph import PropagationGraph, PropagationEdge, TraversalNode
from synapse.event.impact import ImpactAnalyzer, ImpactReport
from synapse.event.integration import EventReviewIntegrator
from synapse.event.datasource import DataSource, MarketData

if TYPE_CHECKING:
    from synapse.event.base import BaseDetector
    from synapse.event.registry import DetectorRegistry
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
    from synapse.event.nlp_detectors import (
        AnnouncementDetector,
        ResearchReportDetector,
        NewsSentimentDetector,
        PolicyDetector_NLP,
        NERDetector,
        EventExtractionDetector,
    )
    from synapse.event.dedup import DeduplicationEngine
    from synapse.event.taxonomy import (
        EVENT_TYPES,
        SOURCE_PRIORITY,
        EVENT_CATEGORY_MAP,
        PRIORITY_LEVELS,
    )

__all__ = [
    # Graph (IMPL-001)
    "PropagationGraph",
    "PropagationEdge",
    "TraversalNode",
    # Detector framework (IMPL-002)
    "BaseDetector",
    "DetectorRegistry",
    # Concrete detectors (IMPL-003)
    "EarningsDetector",
    "PolicyDetector",
    "SentimentDetector",
    "ThemeDetector",
    "CapitalFlowDetector",
    "CorporateActionDetector",
    "PolicyChangeDetector",
    "MacroShiftDetector",
    # NLP detectors (IMPL-008 / F-043)
    "AnnouncementDetector",
    "ResearchReportDetector",
    "NewsSentimentDetector",
    "PolicyDetector_NLP",
    "NERDetector",
    "EventExtractionDetector",
    # Deduplication (IMPL-003)
    "DeduplicationEngine",
    # Taxonomy
    "EVENT_TYPES",
    "SOURCE_PRIORITY",
    "EVENT_CATEGORY_MAP",
    "PRIORITY_LEVELS",
    # Lifecycle + Decay (IMPL-005)
    "PropagationLifecycle",
    "LifecycleState",
    "PropagationState",
    "compute_decay",
    "apply_category_decay",
    "CATEGORY_HALF_LIVES",
    # Impact Analysis (IMPL-006)
    "ImpactAnalyzer",
    "ImpactReport",
    # Integration (IMPL-007)
    "EventReviewIntegrator",
    # Social media sentiment (P4)
    "SocialMediaSignal",
    "LexiconAnalyzer",
    "collect_from_source",
    # Streaming ingestion (P4)
    "PollingSource",
    "StreamBuffer",
    "StreamingIngestion",
    # Data source adapter protocol (P5)
    "DataSource",
    "MarketData",
    "adapter_fetch_fn",
]


def __getattr__(name: str):
    """Lazy import to avoid circular dependency."""
    if name in ("BaseDetector",):
        from synapse.event.base import BaseDetector
        return BaseDetector
    if name in ("DetectorRegistry",):
        from synapse.event.registry import DetectorRegistry
        return DetectorRegistry
    if name in (
        "EarningsDetector", "PolicyDetector", "SentimentDetector",
        "ThemeDetector", "CapitalFlowDetector", "CorporateActionDetector",
        "PolicyChangeDetector", "MacroShiftDetector",
    ):
        from synapse.event import detectors
        return getattr(detectors, name)
    if name in (
        "AnnouncementDetector", "ResearchReportDetector",
        "NewsSentimentDetector", "PolicyDetector_NLP",
        "NERDetector", "EventExtractionDetector",
    ):
        from synapse.event import nlp_detectors
        return getattr(nlp_detectors, name)
    if name in ("DeduplicationEngine",):
        from synapse.event.dedup import DeduplicationEngine
        return DeduplicationEngine
    if name in ("EVENT_TYPES", "SOURCE_PRIORITY", "EVENT_CATEGORY_MAP", "PRIORITY_LEVELS"):
        from synapse.event import taxonomy
        return getattr(taxonomy, name)
    if name in ("PropagationLifecycle", "LifecycleState", "PropagationState", "compute_decay", "apply_category_decay", "CATEGORY_HALF_LIVES"):
        from synapse.event import lifecycle
        return getattr(lifecycle, name)
    if name in ("ImpactAnalyzer", "ImpactReport"):
        from synapse.event import impact
        return getattr(impact, name)
    if name in ("EventReviewIntegrator",):
        from synapse.event.integration import EventReviewIntegrator
        return EventReviewIntegrator
    if name in ("SocialMediaSignal", "LexiconAnalyzer", "collect_from_source"):
        from synapse.event import social
        return getattr(social, name)
    if name in ("PollingSource", "StreamBuffer", "StreamingIngestion"):
        from synapse.event import streaming
        return getattr(streaming, name)
    if name in ("DataSource", "MarketData"):
        from synapse.event import datasource
        return getattr(datasource, name)
    if name in ("adapter_fetch_fn",):
        from synapse.event.adapters import adapter_fetch_fn
        return adapter_fetch_fn
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
