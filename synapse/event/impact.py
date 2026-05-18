"""Event Impact Analyzer -- Computes impact scores for events propagated through graph.

Impact formula:
    impact = severity * confidence * decay_factor * path_weight

Where:
    - severity, confidence: from Event schema (0.0-1.0)
    - decay_factor: e^(-decay_rate * days) via compute_decay()
    - path_weight: product of edge weights along propagation path
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from synapse.core.schemas.event import Event, PropagationState
from synapse.event.graph import MAX_PROPAGATION_DEPTH, PropagationGraph
from synapse.event.lifecycle import compute_decay


@dataclass
class ImpactReport:
    """Impact analysis report for a single event."""

    event_id: str
    direct_impacts: dict[str, float] = field(default_factory=dict)
    cascaded_impacts: dict[str, float] = field(default_factory=dict)
    aggregate_by_position: dict[str, float] = field(default_factory=dict)
    max_impact_entity: str = ""
    total_impact: float = 0.0
    computed_at: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict for storage / transport."""
        return {
            "event_id": self.event_id,
            "direct_impacts": self.direct_impacts,
            "cascaded_impacts": self.cascaded_impacts,
            "aggregate_by_position": self.aggregate_by_position,
            "max_impact_entity": self.max_impact_entity,
            "total_impact": self.total_impact,
            "computed_at": self.computed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ImpactReport:
        """Deserialize from dict."""
        return cls(
            event_id=data["event_id"],
            direct_impacts=data.get("direct_impacts", {}),
            cascaded_impacts=data.get("cascaded_impacts", {}),
            aggregate_by_position=data.get("aggregate_by_position", {}),
            max_impact_entity=data.get("max_impact_entity", ""),
            total_impact=data.get("total_impact", 0.0),
            computed_at=data.get("computed_at", ""),
        )


class ImpactAnalyzer:
    """Computes event impact through the propagation graph.

    Formula: impact = severity * confidence * decay_factor * path_weight
    """

    def __init__(
        self,
        graph: PropagationGraph,
        event: Event,
        days_since_event: float = 0.0,
    ) -> None:
        self._graph = graph
        self._event = event
        self._days = days_since_event

    # ------------------------------------------------------------------
    # Public API -- 4 impact metrics
    # ------------------------------------------------------------------

    def compute_direct_impact(self) -> dict[str, float]:
        """Single-hop impact: event -> direct neighbors (theses).

        Returns dict of {node_id: impact_score} for depth-1 neighbors only.
        """
        downstream = self._graph.bfs_downstream(self._event.id, max_depth=1)
        impacts: dict[str, float] = {}
        for node in downstream:
            if node.depth == 1:
                score = self._compute_score(node.edge_weight)
                if score > 0:
                    impacts[node.node_id] = round(score, 6)
        return impacts

    def compute_cascaded_impact(self) -> dict[str, float]:
        """Multi-hop impact: event -> thesis -> position (path weight product).

        For each reachable node, compute the product of edge weights along
        the best (highest-weight) path, multiplied by severity * confidence
        * decay_factor.
        """
        if not self._graph.has_node(self._event.id):
            return {}

        visited: dict[str, float] = {}  # node_id -> best path weight
        queue: deque[tuple[str, float, int]] = deque(
            [(self._event.id, 1.0, 0)]
        )

        while queue:
            current, path_weight, depth = queue.popleft()
            if depth >= MAX_PROPAGATION_DEPTH:
                continue
            for edge in self._graph.get_outgoing_edges(current):
                new_weight = path_weight * edge.weight
                if edge.target_id not in visited or new_weight > visited[edge.target_id]:
                    visited[edge.target_id] = new_weight
                queue.append((edge.target_id, new_weight, depth + 1))

        impacts: dict[str, float] = {}
        for node_id, path_weight in visited.items():
            score = self._compute_score(path_weight)
            if score > 0:
                impacts[node_id] = round(score, 6)
        return impacts

    def compute_aggregate_impact(
        self, position_ids: Optional[list[str]] = None
    ) -> dict[str, float]:
        """Sum impacts per position.

        If position_ids provided, filter to those positions only.
        """
        cascaded = self.compute_cascaded_impact()
        if position_ids is None:
            return dict(cascaded)
        return {
            pid: cascaded.get(pid, 0.0)
            for pid in position_ids
            if cascaded.get(pid, 0.0) > 0
        }

    def compute_risk_adjusted_impact(
        self,
        portfolio_volatility: float,
        position_ids: Optional[list[str]] = None,
    ) -> dict[str, float]:
        """Divide aggregate impact by portfolio_volatility.

        Args:
            portfolio_volatility: Portfolio-level volatility (> 0).
            position_ids: Optional filter for specific positions.

        Returns:
            Risk-adjusted impact scores, or empty dict if volatility <= 0.
        """
        if portfolio_volatility <= 0:
            return {}
        aggregate = self.compute_aggregate_impact(position_ids)
        return {
            pid: round(score / portfolio_volatility, 6)
            for pid, score in aggregate.items()
        }

    def compute_full_report(
        self, portfolio_volatility: float = 1.0
    ) -> ImpactReport:
        """Compute full impact report with all metrics."""
        direct = self.compute_direct_impact()
        cascaded = self.compute_cascaded_impact()
        aggregate = self.compute_aggregate_impact()

        all_scores: dict[str, float] = {**direct, **cascaded}
        max_entity = max(all_scores, key=all_scores.get) if all_scores else ""
        total = sum(all_scores.values())

        return ImpactReport(
            event_id=self._event.id,
            direct_impacts=direct,
            cascaded_impacts=cascaded,
            aggregate_by_position=aggregate,
            max_impact_entity=max_entity,
            total_impact=round(total, 6),
            computed_at=date.today().isoformat(),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _compute_score(self, path_weight: float) -> float:
        """Core formula: severity * confidence * decay_factor * path_weight."""
        if self._event.propagation_state == PropagationState.EXPIRED:
            return 0.0
        decay_factor = compute_decay(1.0, self._event.decay_rate, self._days)
        return self._event.severity * self._event.confidence * decay_factor * path_weight
