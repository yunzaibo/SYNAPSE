"""PropagationGraph -- DAG with cycle detection, topological sort, and traversal.

Directed acyclic graph for event propagation. Enforces DAG property on every
edge insertion (rejects edges that would create cycles). Uses Tarjan's algorithm
for O(V+E) cycle detection and Kahn's algorithm for deterministic topological sort.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from synapse.core.schemas.event import PropagationState

logger = logging.getLogger(__name__)

MAX_PROPAGATION_DEPTH = 5


@dataclass
class PropagationEdge:
    """Lightweight edge record for graph-internal use.

    This is distinct from synapse.core.schemas.propagation_edge.PropagationEdge
    (the schema-layer object). This one lives purely inside the graph.
    """

    source_id: str
    target_id: str
    weight: float = 0.5
    decay_rate: float = 0.1
    edge_type: str = ""


@dataclass
class TraversalNode:
    """Node encountered during BFS traversal."""

    node_id: str
    depth: int
    edge_weight: float


class PropagationGraph:
    """Directed acyclic graph for event propagation.

    Internal state:
        _adj: dict[str, list[PropagationEdge]]  -- adjacency list (outgoing)
        _in_edges: dict[str, list[PropagationEdge]]  -- reverse index (incoming)
        _nodes: set[str]  -- all known node ids
        _rejected_edges: list[tuple[str, str, str]]  -- audit trail (src, tgt, reason)

    Thread-safety: not thread-safe. Callers must synchronize externally.
    """

    def __init__(self) -> None:
        self._adj: dict[str, list[PropagationEdge]] = {}
        self._in_edges: dict[str, list[PropagationEdge]] = {}
        self._nodes: set[str] = set()
        self._rejected_edges: list[tuple[str, str, str]] = []
        self._node_states: dict[str, PropagationState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        weight: float = 0.5,
        decay_rate: float = 0.1,
        edge_type: str = "",
    ) -> PropagationEdge:
        """Add a directed edge. Rejects self-loops and edges that create cycles.

        Returns the created PropagationEdge on success.
        Raises ValueError if the edge would violate DAG property.
        """
        if source_id == target_id:
            self._rejected_edges.append((source_id, target_id, "self-loop"))
            raise ValueError(f"Self-loop rejected: {source_id} -> {target_id}")

        if self._would_create_cycle(source_id, target_id):
            self._rejected_edges.append((source_id, target_id, "cycle"))
            raise ValueError(
                f"Edge {source_id} -> {target_id} would create a cycle"
            )

        edge = PropagationEdge(
            source_id=source_id,
            target_id=target_id,
            weight=weight,
            decay_rate=decay_rate,
            edge_type=edge_type,
        )

        self._nodes.add(source_id)
        self._nodes.add(target_id)
        self._adj.setdefault(source_id, []).append(edge)
        self._in_edges.setdefault(target_id, []).append(edge)
        return edge

    def remove_edge(self, source_id: str, target_id: str) -> bool:
        """Remove edge(s) from source to target. Returns True if any were removed."""
        removed = False

        # Remove from adjacency list
        if source_id in self._adj:
            before = len(self._adj[source_id])
            self._adj[source_id] = [
                e for e in self._adj[source_id] if e.target_id != target_id
            ]
            removed = removed or (len(self._adj[source_id]) < before)

        # Remove from reverse index
        if target_id in self._in_edges:
            self._in_edges[target_id] = [
                e for e in self._in_edges[target_id] if e.source_id != source_id
            ]

        # Clean up empty entries
        if source_id in self._adj and not self._adj[source_id]:
            del self._adj[source_id]
        if target_id in self._in_edges and not self._in_edges[target_id]:
            del self._in_edges[target_id]

        return removed

    def get_neighbors(self, node_id: str) -> list[str]:
        """Return direct downstream neighbors of node_id."""
        return [e.target_id for e in self._adj.get(node_id, [])]

    def get_all_nodes(self) -> list[str]:
        """Return sorted list of all node ids."""
        return sorted(self._nodes)

    def get_edge(
        self, source_id: str, target_id: str
    ) -> Optional[PropagationEdge]:
        """Return the edge from source to target, or None."""
        for e in self._adj.get(source_id, []):
            if e.target_id == target_id:
                return e
        return None

    def get_roots(self) -> list[str]:
        """Return nodes with no incoming edges (propagation entry points)."""
        return sorted(
            n for n in self._nodes if n not in self._in_edges or not self._in_edges[n]
        )

    def get_rejected_edges(self) -> list[tuple[str, str, str]]:
        """Return audit trail of rejected edges (src, tgt, reason)."""
        return list(self._rejected_edges)

    def has_node(self, node_id: str) -> bool:
        """Return True if node_id is in the graph."""
        return node_id in self._nodes

    def get_outgoing_edges(self, node_id: str) -> list[PropagationEdge]:
        """Return outgoing edges from node_id."""
        return list(self._adj.get(node_id, []))

    # ------------------------------------------------------------------
    # Topological sort (Kahn's algorithm)
    # ------------------------------------------------------------------

    def topological_sort(self) -> list[str]:
        """Return node ids in deterministic topological order (Kahn's algorithm).

        Raises ValueError if the graph contains a cycle (should not happen after
        DAG enforcement, but checked defensively).
        """
        # Build in-degree map
        in_degree: dict[str, int] = {n: 0 for n in self._nodes}
        for node, edges in self._adj.items():
            for e in edges:
                in_degree[e.target_id] = in_degree.get(e.target_id, 0) + 1

        # Seed queue with roots (in-degree 0), sorted for determinism
        queue: deque[str] = deque(sorted(n for n, d in in_degree.items() if d == 0))
        result: list[str] = []

        while queue:
            node = queue.popleft()
            result.append(node)
            for e in self._adj.get(node, []):
                in_degree[e.target_id] -= 1
                if in_degree[e.target_id] == 0:
                    # Insert in sorted position to maintain determinism
                    self._sorted_insert(queue, e.target_id)

        if len(result) != len(self._nodes):
            raise ValueError("Graph contains a cycle; topological sort impossible")

        return result

    # ------------------------------------------------------------------
    # BFS traversal
    # ------------------------------------------------------------------

    def bfs_downstream(
        self, start_id: str, max_depth: int = MAX_PROPAGATION_DEPTH
    ) -> list[TraversalNode]:
        """BFS from start_id following outgoing edges.

        Returns list of TraversalNode(node_id, depth, edge_weight) for all
        reachable nodes up to max_depth levels.
        """
        if start_id not in self._nodes:
            return []

        visited: set[str] = {start_id}
        result: list[TraversalNode] = []
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for e in self._adj.get(current, []):
                if e.target_id not in visited:
                    visited.add(e.target_id)
                    result.append(
                        TraversalNode(
                            node_id=e.target_id, depth=depth + 1, edge_weight=e.weight
                        )
                    )
                    queue.append((e.target_id, depth + 1))

        return result

    def bfs_upstream(
        self, start_id: str, max_depth: int = MAX_PROPAGATION_DEPTH
    ) -> list[TraversalNode]:
        """Reverse BFS from start_id following incoming edges.

        Returns list of TraversalNode(node_id, depth, edge_weight) for all
        upstream sources up to max_depth levels.
        """
        if start_id not in self._nodes:
            return []

        visited: set[str] = {start_id}
        result: list[TraversalNode] = []
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for e in self._in_edges.get(current, []):
                if e.source_id not in visited:
                    visited.add(e.source_id)
                    result.append(
                        TraversalNode(
                            node_id=e.source_id, depth=depth + 1, edge_weight=e.weight
                        )
                    )
                    queue.append((e.source_id, depth + 1))

        return result

    # ------------------------------------------------------------------
    # Lifecycle state tracking
    # ------------------------------------------------------------------

    def update_node_state(self, node_id: str, new_state: PropagationState) -> None:
        """Update the lifecycle state of a node.

        Args:
            node_id: Node to update.
            new_state: New PropagationState value.

        Raises:
            ValueError: If node_id is not in the graph.
        """
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id!r} not in graph")
        self._node_states[node_id] = new_state

    def get_node_state(self, node_id: str) -> Optional[PropagationState]:
        """Return lifecycle state of a node, or None if not tracked."""
        return self._node_states.get(node_id)

    def get_expired_nodes(self) -> list[str]:
        """Return sorted list of nodes in EXPIRED state."""
        from synapse.core.schemas.event import PropagationState as PS

        return sorted(
            n for n, s in self._node_states.items() if s == PS.EXPIRED
        )

    def apply_decay_to_edges(self, days: float) -> dict[str, float]:
        """Apply exponential decay to all edge weights (idempotent).

        Stores original weights on first call; subsequent calls recompute
        from originals, preventing double-decay.

        Args:
            days: Elapsed time in days.

        Returns:
            Dict of "{source_id}->{target_id}" -> decayed_weight.
        """
        # Store original weights on first invocation (idempotency guard)
        for node_id, edges in self._adj.items():
            for edge in edges:
                if not hasattr(edge, "_original_weight"):
                    edge._original_weight = edge.weight  # type: ignore[attr-defined]

        results: dict[str, float] = {}
        for node_id, edges in self._adj.items():
            for edge in edges:
                original = edge._original_weight  # type: ignore[attr-defined]
                decayed = original * math.exp(-edge.decay_rate * days)
                edge.weight = decayed
                edge_key = f"{edge.source_id}->{edge.target_id}"
                results[edge_key] = decayed
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _would_create_cycle(self, source_id: str, target_id: str) -> bool:
        """Check if adding edge (source -> target) would create a cycle.

        Uses BFS from target following outgoing edges. If we can reach source,
        adding the edge would close a cycle.
        """
        # If target is not yet in the graph, no cycle possible
        if target_id not in self._nodes:
            return False

        # BFS from target, check if source is reachable
        visited: set[str] = set()
        queue: deque[str] = deque([target_id])

        while queue:
            node = queue.popleft()
            if node == source_id:
                return True
            if node in visited:
                continue
            visited.add(node)
            for e in self._adj.get(node, []):
                if e.target_id not in visited:
                    queue.append(e.target_id)

        return False

    @staticmethod
    def _sorted_insert(queue: deque[str], value: str) -> None:
        """Insert value into a deque maintaining sorted order (for determinism).

        Complexity: O(n) per call due to linear scan of the deque.  In the
        topological-sort context the queue never exceeds the number of graph
        nodes with zero in-degree, so linear insertion is acceptable for
        typical graph sizes (< 10k nodes).  For very large graphs, consider
        replacing the deque with a sorted container (e.g. ``sortedcontainers.SortedList``)
        to achieve O(log n) insertion.
        """
        inserted = False
        temp: list[str] = []
        while queue and queue[0] < value:
            temp.append(queue.popleft())
        queue.appendleft(value)
        for item in reversed(temp):
            queue.appendleft(item)
