"""Sentiment Propagation -- Viral coefficient (R0) and cascade detection.

Models sentiment propagation through the market graph using standard
epidemiological R0 (reproduction number) and cascade detection.

Cascade = R0 > 1.0 AND propagation depth >= 2 levels.

Uses BFS from root event through edges with edge_type="sentiment".
Duck-typing with hasattr guards for cross-module imports.
"""

from __future__ import annotations

import math
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SentimentPropagation:
    """Schema for sentiment viral propagation metrics.

    Tracks R0 (viral coefficient), cascade depth, and intensity decay
    for a sentiment propagation wave originating from a root event.
    """

    root_event_id: str = ""
    viral_coefficient: float = 0.0
    cascade_depth: int = 0
    cascade_count: int = 0
    intensity_at_source: float = 0.5
    intensity_decay: dict[str, float] = field(default_factory=dict)
    propagation_window_hours: int = 24
    detected_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.root_event_id:
            self.root_event_id = str(uuid.uuid4())
        if self.detected_at is None:
            self.detected_at = datetime.now()
        # Validate ranges
        self._clamp("viral_coefficient", self.viral_coefficient, 0.0, None)
        self._clamp("intensity_at_source", self.intensity_at_source, 0.0, 1.0)

    @staticmethod
    def _clamp(name: str, value: float, lo: float, hi: Optional[float]) -> None:
        """Validate field is >= lo (and <= hi if hi is set)."""
        if value < lo:
            raise ValueError(f"{name} must be >= {lo}, got {value}")
        if hi is not None and value > hi:
            raise ValueError(f"{name} must be <= {hi}, got {value}")

    def to_dict(self) -> dict:
        """Serialize to dict for YAML/JSON output."""
        return {
            "root_event_id": self.root_event_id,
            "viral_coefficient": self.viral_coefficient,
            "cascade_depth": self.cascade_depth,
            "cascade_count": self.cascade_count,
            "intensity_at_source": self.intensity_at_source,
            "intensity_decay": dict(self.intensity_decay),
            "propagation_window_hours": self.propagation_window_hours,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SentimentPropagation:
        """Deserialize from dict with Lazy Upcast defaults."""
        return cls(
            root_event_id=data.get("root_event_id", ""),
            viral_coefficient=float(data.get("viral_coefficient", 0.0)),
            cascade_depth=int(data.get("cascade_depth", 0)),
            cascade_count=int(data.get("cascade_count", 0)),
            intensity_at_source=float(data.get("intensity_at_source", 0.5)),
            intensity_decay=data.get("intensity_decay", {}),
            propagation_window_hours=int(data.get("propagation_window_hours", 24)),
            detected_at=(
                datetime.fromisoformat(data["detected_at"])
                if data.get("detected_at")
                else None
            ),
        )


# ---------------------------------------------------------------------------
# Viral Coefficient (R0)
# ---------------------------------------------------------------------------


def compute_viral_coefficient(graph: object, root_event_id: str) -> float:
    """Compute R0 (viral coefficient) via BFS on sentiment edges.

    R0 = (total_activated_nodes - 1) / direct_children
    where direct_children = nodes at BFS depth 1 from root.

    Args:
        graph: PropagationGraph instance (duck-typed to avoid circular import).
        root_event_id: ID of the root sentiment event.

    Returns:
        R0 value. 0.0 if no downstream activation or root not in graph.
    """
    if not hasattr(graph, "get_outgoing_edges") or not hasattr(graph, "has_node"):
        return 0.0

    if not graph.has_node(root_event_id):  # type: ignore[attr-defined]
        return 0.0

    # BFS through sentiment edges only
    visited: set[str] = {root_event_id}
    queue: deque[tuple[str, int]] = deque([(root_event_id, 0)])
    nodes_by_level: dict[int, list[str]] = {0: [root_event_id]}

    while queue:
        current, depth = queue.popleft()
        for edge in graph.get_outgoing_edges(current):  # type: ignore[attr-defined]
            edge_type = getattr(edge, "edge_type", "")
            if edge_type != "sentiment":
                continue
            target = getattr(edge, "target_id", "")
            if target and target not in visited:
                visited.add(target)
                level = depth + 1
                nodes_by_level.setdefault(level, []).append(target)
                queue.append((target, level))

    # Total activated (excluding root)
    total_activated = len(visited) - 1
    if total_activated == 0:
        return 0.0

    # direct_children = nodes at level 1
    direct_children = len(nodes_by_level.get(1, []))
    if direct_children == 0:
        return 0.0

    return (total_activated - 1) / direct_children


# ---------------------------------------------------------------------------
# Cascade Detection
# ---------------------------------------------------------------------------


def detect_cascade(propagation: SentimentPropagation) -> bool:
    """Detect if a sentiment propagation qualifies as a cascade.

    Cascade criteria: R0 > 1.0 AND cascade_depth >= 2.

    Args:
        propagation: SentimentPropagation with computed metrics.

    Returns:
        True if cascade conditions are met.
    """
    return propagation.viral_coefficient > 1.0 and propagation.cascade_depth >= 2


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_sentiment_propagation(
    root_event: object,
    child_events: list[object],
    graph: object,
) -> SentimentPropagation:
    """Build a SentimentPropagation from graph traversal.

    Traverses the propagation graph from root_event through sentiment edges,
    computes R0, cascade depth, direct children count, and intensity decay.

    Args:
        root_event: Root sentiment event (duck-typed, needs .id, .severity).
        child_events: Downstream events (unused, kept for API compatibility).
        graph: PropagationGraph instance (duck-typed).

    Returns:
        Populated SentimentPropagation.
    """
    root_id = getattr(root_event, "id", "")
    severity = float(getattr(root_event, "severity", 0.5))

    viral_coeff = compute_viral_coefficient(graph, root_id)

    # BFS for depth, cascade_count, and intensity decay
    cascade_depth = 0
    cascade_count = 0
    intensity_decay: dict[str, float] = {}

    if hasattr(graph, "has_node") and graph.has_node(root_id):  # type: ignore[attr-defined]
        from synapse.event.lifecycle import CATEGORY_HALF_LIVES, DEFAULT_HALF_LIFE

        half_life = CATEGORY_HALF_LIVES.get("sentiment", DEFAULT_HALF_LIFE)
        decay_rate = math.log(2) / half_life

        visited: set[str] = {root_id}
        queue: deque[tuple[str, int, float]] = deque([(root_id, 0, severity)])

        while queue:
            current, depth, parent_intensity = queue.popleft()
            for edge in graph.get_outgoing_edges(current):  # type: ignore[attr-defined]
                edge_type = getattr(edge, "edge_type", "")
                if edge_type != "sentiment":
                    continue
                target = getattr(edge, "target_id", "")
                weight = float(getattr(edge, "weight", 0.5))
                if target and target not in visited:
                    visited.add(target)
                    new_depth = depth + 1
                    cascade_depth = max(cascade_depth, new_depth)
                    # Intensity = parent * edge weight, decayed by hop distance
                    child_intensity = parent_intensity * weight * math.exp(
                        -decay_rate * new_depth
                    )
                    intensity_decay[target] = child_intensity
                    if new_depth == 1:
                        cascade_count += 1
                    queue.append((target, new_depth, child_intensity))

    return SentimentPropagation(
        root_event_id=root_id,
        viral_coefficient=viral_coeff,
        cascade_depth=cascade_depth,
        cascade_count=cascade_count,
        intensity_at_source=severity,
        intensity_decay=intensity_decay,
        detected_at=datetime.now(),
    )
