# F-003: Event Propagation Graph

## Component #10: DAG Propagation with Cycle Detection

### Overview
Directed acyclic graph representing event → thesis → position influence paths. Uses adjacency list representation with topological sort for deterministic execution.

### State Machine
```
detected → propagating → settled → expired
                  ↓
              expired (stuck protection, 7-day timeout)
```

### Graph Algorithms
1. **Cycle Detection**: Tarjan's algorithm (O(V+E))
2. **Topological Sort**: Kahn's algorithm for deterministic propagation order
3. **BFS Traversal**: For downstream impact discovery
4. **Reverse BFS**: For upstream source discovery

### Propagation Rules
| Priority | Event Type | Affected Entities | Latency |
|----------|-----------|-------------------|---------|
| P0 (immediate) | earnings, policy | direct theses | < 1 hour |
| P1 (same day) | corporate_action, sentiment | direct theses + positions | < 4 hours |
| P2 (next day) | theme | related theses | < 1 day |
| P3 (within 3 days) | capital_flow | portfolio positions | < 3 days |

### Decay Model
- Exponential decay: `impact(t) = impact_0 * e^(-decay_rate * t)`
- Category-specific half-lives:
  - Earnings surprise: 5-8 days
  - PBOC policy: 1-2 days
  - Northbound flow: 1-3 days
  - Theme/sector: 3-5 days

### Cycle Prevention
- Validate DAG property before edge insertion
- Reject edges that would create cycles
- Log rejected edges for audit trail
- Maximum propagation depth: 5 levels

### Tests (~18 tests)
- Cycle detection: self-loop, 2-node, 3-node, N-node cycles
- DAG validation after edge insertion
- Topological sort determinism
- BFS traversal correctness
- Reverse BFS source discovery
- Decay calculation accuracy
- Stuck protection timeout
- Maximum depth enforcement
- Determinism: same inputs → same graph
