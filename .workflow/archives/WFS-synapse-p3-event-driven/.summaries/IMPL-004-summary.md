# Task: IMPL-004 PropagationGraph Core - DAG, Cycle Detection, Topological Sort

## Implementation Summary

### Files Created/Modified

- `synapse/event/graph.py` (create): PropagationGraph class with adjacency list, cycle detection, topological sort, BFS traversal, depth enforcement
- `synapse/event/__init__.py` (create): Module init with lazy imports for future detector framework
- `tests/unit/test_propagation_graph.py` (create): 15 tests across 5 test classes

### Content Added

**PropagationGraph** (`synapse/event/graph.py`):
- `__init__()`: Initializes adjacency list `_adj`, reverse index `_in_edges`, node registry `_nodes`, rejected edges audit `_rejected_edges`
- `add_edge(source_id, target_id, weight, decay_rate, edge_type)`: Adds directed edge, validates DAG property before insertion. Raises ValueError on self-loops or cycle-creating edges
- `remove_edge(source_id, target_id)`: Removes edge(s) from source to target, returns True if any removed
- `get_neighbors(node_id)`: Returns list of direct downstream neighbor node IDs
- `get_all_nodes()`: Returns sorted list of all node IDs
- `get_edge(source_id, target_id)`: Returns PropagationEdge or None
- `get_roots()`: Returns sorted list of nodes with no incoming edges
- `get_rejected_edges()`: Returns audit trail of rejected edges (src, tgt, reason)
- `topological_sort()`: Kahn's algorithm with deterministic sorted queue, returns node IDs in propagation order
- `bfs_downstream(start_id, max_depth=5)`: BFS following outgoing edges, returns list of TraversalNode(node_id, depth, edge_weight)
- `bfs_upstream(start_id, max_depth=5)`: Reverse BFS following incoming edges, returns list of TraversalNode

**PropagationEdge** (`synapse/event/graph.py:21`):
- Lightweight edge record: source_id, target_id, weight, decay_rate, edge_type

**TraversalNode** (`synapse/event/graph.py:33`):
- BFS result record: node_id, depth, edge_weight

**Constants**:
- `MAX_PROPAGATION_DEPTH = 5` (`synapse/event/graph.py:11`): Default maximum propagation depth

### Internal Helpers

- `_would_create_cycle(source_id, target_id)`: BFS from target checking if source is reachable (cycle = reachability)
- `_sorted_insert(queue, value)`: Maintains sorted order in deque for deterministic Kahn's algorithm

## Outputs for Dependent Tasks

### Available Components

```python
from synapse.event.graph import PropagationGraph, PropagationEdge, TraversalNode, MAX_PROPAGATION_DEPTH

# IMPL-005 (Lifecycle + Decay) will use:
graph = PropagationGraph()
graph.add_edge(source_id="evt-001", target_id="ths-001", weight=0.8, decay_rate=0.1, edge_type="causal")
order = graph.topological_sort()  # deterministic propagation order
downstream = graph.bfs_downstream("evt-001", max_depth=5)
```

### Integration Points

- **PropagationGraph**: Core data structure for event propagation lifecycle (IMPL-005)
- **topological_sort()**: Determines propagation execution order
- **bfs_downstream/bfs_upstream**: Used by Impact Analyzer (IMPL-006) for impact traversal
- **rejected_edges audit trail**: Useful for debugging propagation failures

### Key Properties

- DAG enforcement: Self-loops and cycle-creating edges rejected on insertion
- Deterministic: Same edge set produces same topological order regardless of insertion order
- Depth-limited: BFS traversal enforces max_depth=5 by default
- O(V+E) cycle detection via reachability check

## Status: Complete
