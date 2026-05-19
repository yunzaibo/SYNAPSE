"""Cross-Event Correlation -- Correlation engine with affinity matrix and impact computation.

Correlates events that affect overlapping theses/positions, computes combined
impact, and identifies event clusters that amplify or dampen each other.

Part of the event-driven propagation graph (P3).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass
class EventCorrelation:
    """Schema for cross-event correlation results.

    Tracks correlated event pairs/clusters, their correlation score,
    combined impact, and amplification classification.
    """

    correlation_id: str = ""
    event_ids: list[str] = field(default_factory=list)
    thesis_id: str = ""
    correlation_score: float = 0.0  # [0, 1] strength
    combined_impact: float = 0.0  # Aggregated impact
    amplification: str = "neutral"  # "amplification" / "dampening" / "neutral"
    correlation_window_days: int = 7
    detected_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.correlation_id:
            self.correlation_id = f"corr-{uuid.uuid4().hex[:8]}"
        if self.detected_at is None:
            self.detected_at = datetime.now()
        # Validate ranges
        if not (0.0 <= self.correlation_score <= 1.0):
            raise ValueError(
                f"correlation_score must be in [0, 1], got {self.correlation_score}"
            )
        if not (0.0 <= self.combined_impact <= 2.0):
            raise ValueError(
                f"combined_impact must be in [0, 2], got {self.combined_impact}"
            )

    def to_dict(self) -> dict:
        """Serialize to dict for YAML/JSON round-trip."""
        return {
            "correlation_id": self.correlation_id,
            "event_ids": list(self.event_ids),
            "thesis_id": self.thesis_id,
            "correlation_score": self.correlation_score,
            "combined_impact": self.combined_impact,
            "amplification": self.amplification,
            "correlation_window_days": self.correlation_window_days,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EventCorrelation:
        """Deserialize from dict (Lazy Upcast compatible)."""
        detected_raw = data.get("detected_at")
        return cls(
            correlation_id=data.get("correlation_id", ""),
            event_ids=list(data.get("event_ids", [])),
            thesis_id=data.get("thesis_id", ""),
            correlation_score=float(data.get("correlation_score", 0.0)),
            combined_impact=float(data.get("combined_impact", 0.0)),
            amplification=data.get("amplification", "neutral"),
            correlation_window_days=int(data.get("correlation_window_days", 7)),
            detected_at=(
                datetime.fromisoformat(detected_raw) if detected_raw else None
            ),
        )


# ---------------------------------------------------------------------------
# Event Type Affinity Matrix (9x9)
# ---------------------------------------------------------------------------

# Event type constants (string-based to avoid hard dependency on EventType enum)
TYPE_EARNINGS = "EARNINGS_SURPRISE"
TYPE_POLICY = "POLICY_SHIFT"
TYPE_REGULATORY = "REGULATORY_ACTION"
TYPE_CAPITAL = "CAPITAL_FLOW"
TYPE_SENTIMENT = "MARKET_SENTIMENT"
TYPE_GEO = "GEOPOLITICAL"
TYPE_SECTOR = "SECTOR_ROTATION"
TYPE_MACRO = "MACRO_SHIFT"
TYPE_SOCIAL = "SOCIAL_SENTIMENT"

EVENT_TYPE_AFFINITY: dict[str, dict[str, float]] = {
    TYPE_EARNINGS: {
        TYPE_EARNINGS: 1.0,
        TYPE_POLICY: 0.3,
        TYPE_REGULATORY: 0.2,
        TYPE_CAPITAL: 0.4,
        TYPE_SENTIMENT: 0.5,
        TYPE_GEO: 0.1,
        TYPE_SECTOR: 0.4,
        TYPE_MACRO: 0.3,
        TYPE_SOCIAL: 0.4,
    },
    TYPE_POLICY: {
        TYPE_EARNINGS: 0.3,
        TYPE_POLICY: 1.0,
        TYPE_REGULATORY: 0.8,
        TYPE_CAPITAL: 0.3,
        TYPE_SENTIMENT: 0.4,
        TYPE_GEO: 0.3,
        TYPE_SECTOR: 0.6,
        TYPE_MACRO: 0.5,
        TYPE_SOCIAL: 0.5,
    },
    TYPE_REGULATORY: {
        TYPE_EARNINGS: 0.2,
        TYPE_POLICY: 0.8,
        TYPE_REGULATORY: 1.0,
        TYPE_CAPITAL: 0.2,
        TYPE_SENTIMENT: 0.3,
        TYPE_GEO: 0.2,
        TYPE_SECTOR: 0.5,
        TYPE_MACRO: 0.4,
        TYPE_SOCIAL: 0.4,
    },
    TYPE_CAPITAL: {
        TYPE_EARNINGS: 0.4,
        TYPE_POLICY: 0.3,
        TYPE_REGULATORY: 0.2,
        TYPE_CAPITAL: 1.0,
        TYPE_SENTIMENT: 0.7,
        TYPE_GEO: 0.2,
        TYPE_SECTOR: 0.4,
        TYPE_MACRO: 0.5,
        TYPE_SOCIAL: 0.6,
    },
    TYPE_SENTIMENT: {
        TYPE_EARNINGS: 0.5,
        TYPE_POLICY: 0.4,
        TYPE_REGULATORY: 0.3,
        TYPE_CAPITAL: 0.7,
        TYPE_SENTIMENT: 1.0,
        TYPE_GEO: 0.3,
        TYPE_SECTOR: 0.5,
        TYPE_MACRO: 0.4,
        TYPE_SOCIAL: 0.8,
    },
    TYPE_GEO: {
        TYPE_EARNINGS: 0.1,
        TYPE_POLICY: 0.3,
        TYPE_REGULATORY: 0.2,
        TYPE_CAPITAL: 0.2,
        TYPE_SENTIMENT: 0.3,
        TYPE_GEO: 1.0,
        TYPE_SECTOR: 0.4,
        TYPE_MACRO: 0.6,
        TYPE_SOCIAL: 0.3,
    },
    TYPE_SECTOR: {
        TYPE_EARNINGS: 0.4,
        TYPE_POLICY: 0.6,
        TYPE_REGULATORY: 0.5,
        TYPE_CAPITAL: 0.4,
        TYPE_SENTIMENT: 0.5,
        TYPE_GEO: 0.4,
        TYPE_SECTOR: 1.0,
        TYPE_MACRO: 0.3,
        TYPE_SOCIAL: 0.5,
    },
    TYPE_MACRO: {
        TYPE_EARNINGS: 0.3,
        TYPE_POLICY: 0.5,
        TYPE_REGULATORY: 0.4,
        TYPE_CAPITAL: 0.5,
        TYPE_SENTIMENT: 0.4,
        TYPE_GEO: 0.6,
        TYPE_SECTOR: 0.3,
        TYPE_MACRO: 1.0,
        TYPE_SOCIAL: 0.4,
    },
    TYPE_SOCIAL: {
        TYPE_EARNINGS: 0.4,
        TYPE_POLICY: 0.5,
        TYPE_REGULATORY: 0.4,
        TYPE_CAPITAL: 0.6,
        TYPE_SENTIMENT: 0.8,
        TYPE_GEO: 0.3,
        TYPE_SECTOR: 0.5,
        TYPE_MACRO: 0.4,
        TYPE_SOCIAL: 1.0,
    },
}


# ---------------------------------------------------------------------------
# Correlation Scoring
# ---------------------------------------------------------------------------


def compute_correlation_score(
    event_a: Any,
    event_b: Any,
    time_proximity: float,
) -> float:
    """Compute correlation score between two events.

    Formula: type_affinity x temporal_proximity
    where temporal_proximity is a pre-computed value in [0, 1].

    Parameters
    ----------
    event_a:
        First event (duck-typed, needs .event_type).
    event_b:
        Second event (duck-typed, needs .event_type).
    time_proximity:
        Pre-computed temporal proximity in [0, 1]. 1.0 = same time,
        0.0 = at or beyond window edge.

    Returns
    -------
    float in [0, 1]. Higher = stronger correlation.
    """
    type_a = getattr(event_a, "event_type", "")
    type_b = getattr(event_b, "event_type", "")

    # Type affinity lookup with fallback
    type_row = EVENT_TYPE_AFFINITY.get(str(type_a), {})
    affinity = type_row.get(str(type_b), 0.0)

    # Clamp temporal_proximity to [0, 1]
    proximity = max(0.0, min(1.0, time_proximity))

    return affinity * proximity


def classify_amplification(score: float) -> str:
    """Classify correlation score as amplification, dampening, or neutral.

    Thresholds:
    - score > 0.6 -> "amplification"
    - score < 0.3 -> "dampening"
    - otherwise   -> "neutral"

    Parameters
    ----------
    score:
        Correlation score in [0, 1].

    Returns
    -------
    One of "amplification", "dampening", "neutral".
    """
    if score > 0.6:
        return "amplification"
    if score < 0.3:
        return "dampening"
    return "neutral"


def compute_combined_impact(events: list[Any]) -> float:
    """Compute combined impact from a cluster of correlated events.

    Aggregates severity from multiple events, applying amplification or
    dampening based on the correlation score between pairs.

    Parameters
    ----------
    events:
        List of event-like objects (duck-typed, needs .severity and .event_type).

    Returns
    -------
    float: Combined impact score.
    """
    if not events:
        return 0.0

    if len(events) == 1:
        return float(getattr(events[0], "severity", 0.5))

    # Pairwise combined impact
    total_impact = 0.0
    pair_count = 0

    for ev_a, ev_b in combinations(events, 2):
        type_a = getattr(ev_a, "event_type", "")
        type_b = getattr(ev_b, "event_type", "")
        sev_a = float(getattr(ev_a, "severity", 0.5))
        sev_b = float(getattr(ev_b, "severity", 0.5))

        # Compute correlation for this pair (assume co-temporal for aggregation)
        score = compute_correlation_score(ev_a, ev_b, 1.0)
        amp_class = classify_amplification(score)

        # Combined impact formula from F-009 spec
        max_sev = max(sev_a, sev_b)
        if amp_class == "amplification":
            combined = max_sev * (1.0 + score * 0.5)
        elif amp_class == "dampening":
            combined = max_sev * (1.0 - score * 0.3)
        else:
            combined = max_sev

        total_impact += combined
        pair_count += 1

    return total_impact / pair_count if pair_count > 0 else 0.0


def find_correlations(
    events: list[Any],
    window_days: int = 7,
    max_cluster: int = 10,
) -> list[EventCorrelation]:
    """Find correlations between events within a time window.

    Performs pairwise comparison of events, computing correlation scores
    and creating EventCorrelation records for pairs that exceed the
    correlation threshold.

    Parameters
    ----------
    events:
        List of event-like objects (duck-typed, needs .id, .event_type,
        .timestamp, .severity, .thesis_id).
    window_days:
        Time window in days for correlation detection.
    max_cluster:
        Maximum cluster size for O(n^2) performance bound.

    Returns
    -------
    list[EventCorrelation]: Detected correlations, sorted by score descending.
    """
    if len(events) < 2:
        return []

    # Limit cluster size for performance
    limited_events = events[:max_cluster]

    correlations: list[EventCorrelation] = []

    for ev_a, ev_b in combinations(limited_events, 2):
        # Duck-typed attribute access
        id_a = getattr(ev_a, "id", "")
        id_b = getattr(ev_b, "id", "")
        type_a = getattr(ev_a, "event_type", "")
        type_b = getattr(ev_b, "event_type", "")
        ts_a = getattr(ev_a, "timestamp", None)
        ts_b = getattr(ev_b, "timestamp", None)
        thesis_a = getattr(ev_a, "thesis_id", "")
        thesis_b = getattr(ev_b, "thesis_id", "")

        # Skip if no shared thesis
        if not thesis_a or thesis_a != thesis_b:
            continue

        # Skip if timestamps are missing
        if ts_a is None or ts_b is None:
            continue

        # Parse timestamps if strings
        if isinstance(ts_a, str):
            ts_a = datetime.fromisoformat(ts_a)
        if isinstance(ts_b, str):
            ts_b = datetime.fromisoformat(ts_b)

        days_between = abs((ts_a - ts_b).total_seconds()) / 86400.0

        # Skip if outside window
        if days_between > window_days:
            continue

        # Compute temporal proximity and correlation score
        time_proximity = max(0.0, 1.0 - (days_between / window_days))
        score = compute_correlation_score(ev_a, ev_b, time_proximity)

        # Skip low correlations
        if score < 0.1:
            continue

        # Compute combined impact
        amp_class = classify_amplification(score)
        sev_a = float(getattr(ev_a, "severity", 0.5))
        sev_b = float(getattr(ev_b, "severity", 0.5))
        max_sev = max(sev_a, sev_b)

        if amp_class == "amplification":
            combined = max_sev * (1.0 + score * 0.5)
        elif amp_class == "dampening":
            combined = max_sev * (1.0 - score * 0.3)
        else:
            combined = max_sev

        correlations.append(
            EventCorrelation(
                event_ids=[id_a, id_b],
                thesis_id=thesis_a,
                correlation_score=score,
                combined_impact=combined,
                amplification=amp_class,
                correlation_window_days=window_days,
            )
        )

    # Sort by score descending
    correlations.sort(key=lambda c: c.correlation_score, reverse=True)

    return correlations


def add_correlation_edges(
    graph: Any,
    correlations: list[EventCorrelation],
    graph_module: Any = None,
) -> list[Any]:
    """Add correlation edges to PropagationGraph (single-direction, DAG-safe).

    Uses deterministic ordering (min_id -> max_id) to ensure single-direction
    edges that preserve the DAG property (no cycles).

    Parameters
    ----------
    graph:
        PropagationGraph instance (duck-typed).
    correlations:
        List of EventCorrelation objects to add as edges.
    graph_module:
        Optional module containing PropagationEdge for type checking.

    Returns
    -------
    list: Added edges (PropagationEdge objects or dicts).
    """
    added_edges: list[Any] = []

    if not hasattr(graph, "add_edge"):
        return added_edges

    for corr in correlations:
        if len(corr.event_ids) < 2:
            continue

        # Single-direction: min_id -> max_id (DAG-safe, no cycles)
        sorted_ids = sorted(corr.event_ids[:2])
        source_id, target_id = sorted_ids[0], sorted_ids[1]

        # Skip if source == target (shouldn't happen, but defensive)
        if source_id == target_id:
            continue

        try:
            edge = graph.add_edge(
                source_id=source_id,
                target_id=target_id,
                weight=corr.correlation_score,
                decay_rate=0.05,  # Correlation edges decay slower
                edge_type="correlation",
            )
            added_edges.append(edge)
        except ValueError:
            # Edge would create a cycle or is a self-loop -- skip
            logger.debug(
                "Skipped correlation edge %s -> %s (would create cycle)",
                source_id,
                target_id,
            )
            continue

    return added_edges
