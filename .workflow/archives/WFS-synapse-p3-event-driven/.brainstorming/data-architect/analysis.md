# Data Architect Analysis: P3 Event-Driven Research Contracts

## Role Perspective Overview

This analysis approaches P3 from a data architecture perspective: how Event, EventContract, and PropagationEdge schemas extend the existing 11-schema system, how propagation graphs are stored and queried, and how Lazy Upcast migration remains viable. The analysis prioritizes storage efficiency for graph traversals, backward compatibility, and query patterns that P4 analytics will rely on.

---

## 1. Data Architecture Overview

### 1.1 Business Context

SYNAPSE is an AI-native Quant Research OS. P0-P2 established 11 schemas (Base, WatchlistEntry, Thesis, Decision, Review, Position, Signal, Risk, Event, ResearchTopic) and 7 analytics components. P3 adds event-driven research contracts: the ability to detect market events, link them to theses/positions via propagation graphs, and track impact decay over time.

The core data challenge is representing a directed propagation graph (event -> thesis -> position) within a file-based YAML storage system that currently has no graph-native capabilities.

### 1.2 Data Strategy

- **Storage model**: YAML files on disk (consistent with P0-P2), no external database
- **Schema evolution**: Lazy Upcast via `schema_version` field (proven in P2)
- **Graph representation**: Embedded edge lists within schema objects (not a separate graph database)
- **Query strategy**: In-memory graph construction at query time from YAML files
- **Projection model**: EventContract is rebuildable from raw Event + PropagationEdge data

### 1.3 Success Criteria

- Event schema v3.0 readable by existing v2.0 consumers without modification
- Propagation graph traversable in < 100ms for graphs up to 1000 edges
- Zero data loss during Lazy Upcast migration
- EventContract projection deterministic: same inputs produce identical outputs

---

## 2. Data Requirements Analysis

### 2.1 Functional Requirements

**Core Entities (new for P3)**:

| Entity | Purpose | Volume Estimate |
|--------|---------|----------------|
| Event (v3.0) | Extended market event record | ~50-200/year |
| EventContract | Links event to affected theses/positions | ~100-500/year |
| PropagationEdge | Directed graph edge with weight/decay | ~200-2000/year |

**Operations**:

| Operation | Entity | Description |
|-----------|--------|-------------|
| CREATE | Event | Detect new event, assign type/confidence |
| EXTEND | Event | Add propagation_state transitions |
| CREATE | EventContract | Link event to affected entities after detection |
| CREATE | PropagationEdge | Record influence path between entities |
| QUERY | PropagationEdge | Find all downstream effects of an event |
| QUERY | EventContract | Aggregate impact scores per position |
| UPDATE | PropagationEdge | Apply decay, update weight |
| RETIRE | EventContract | Settle contract when event impact expires |

### 2.2 Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| Graph traversal latency | < 100ms for 1000 edges | CLI responsiveness |
| Storage overhead per event | < 5KB | YAML file size consistency |
| Backward compatibility | v2.0 consumers read v3.0 files | Lazy Upcast contract |
| Determinism | Same inputs -> same projection | Reproducible analytics |
| Cycle detection | < 10ms for 1000 edges | Prevent infinite propagation |

### 2.3 Data Quality Requirements

- **Completeness**: Every PropagationEdge MUST have valid source_id and target_id referencing existing entities
- **Consistency**: EventContract.impact_scores keys MUST match affected_theses + affected_positions
- **Timeliness**: propagation_state MUST reflect latest edge state
- **Accuracy**: weight values MUST be in [0.0, 1.0]; decay values MUST be non-negative

---

## 3. Data Model Design

### 3.1 Conceptual Model

```
                    +-------------------+
                    |       Event       |
                    |   (v3.0 extend)   |
                    +--------+----------+
                             |
                    links via event_id
                             |
              +--------------+--------------+
              |                             |
    +---------v----------+     +-----------v----------+
    |   EventContract    |     |  PropagationEdge     |
    | (impact aggregator)|     | (graph edge)         |
    +----+------+--------+     +--+------+-----+------+
         |      |                 |      |     |
    links to  links to        source  target  weight/decay
         |      |                 |      |
    +----v--+ +-v------+    +----v--+ +-v--------+
    |Thesis | |Position|    |Thesis| |Position  |
    +-------+ +--------+    +------+ +----------+
```

### 3.2 Logical Model: Event Schema v3.0 Extension

The existing Event schema (v2.0) at `synapse/core/schemas/event.py` already has:
- `event_type: EventType` (enum: earnings, policy, product_launch, management_change, sector_rotation, macro_data)
- `impact_level: ImpactLevel` (enum: low, medium, high, unknown)
- `outcome_tracking: list[OutcomeRecord]` (P2 analytics)
- `linked_review_ids: list[str]`
- `calibration_score: Optional[float]`

**New fields for v3.0** (additive, no removals):

```python
class PropagationState(str, Enum):
    """Lifecycle state for event propagation."""
    DETECTED = "detected"       # Event just detected, not yet linked
    PROPAGATING = "propagating" # Edges being created
    SETTLED = "settled"         # All impacts assessed
    EXPIRED = "expired"         # Decay has reduced all edges below threshold


class EventSource(str, Enum):
    """Origin of event detection."""
    DATA_FEED = "data_feed"
    NEWS = "news"
    MANUAL = "manual"
    AI_DETECTED = "ai_detected"


@dataclass
class Event(BaseSchema):
    """Market event of interest — v3.0 with propagation support."""

    schema_version: str = "3.0"  # bumped from "2.0"

    # --- Core (unchanged from v2.0) ---
    event_type: EventType = EventType.EARNINGS
    title: str = ""
    description: str = ""
    event_date: Optional[date] = None

    # --- Related (unchanged) ---
    related_tickers: list[str] = field(default_factory=list)

    # --- Impact Assessment (unchanged) ---
    impact_level: ImpactLevel = ImpactLevel.UNKNOWN

    # --- Outcome Tracking P2 (unchanged) ---
    outcome_tracking: list[OutcomeRecord] = field(default_factory=list)
    linked_review_ids: list[str] = field(default_factory=list)
    calibration_score: Optional[float] = None

    # --- NEW: Propagation fields (v3.0) ---
    confidence: float = 0.5              # 0.0-1.0, detection confidence
    severity: float = 0.5                # 0.0-1.0, event severity
    decay_rate: float = 0.1              # per-day decay factor
    source: EventSource = EventSource.MANUAL
    propagation_state: PropagationState = PropagationState.DETECTED
    propagation_graph_id: Optional[str] = None  # links to graph root
    contract_id: Optional[str] = None           # links to EventContract
```

**Backward Compatibility Analysis**:

| Consumer | v2.0 reads v3.0? | Risk | Mitigation |
|----------|-------------------|------|------------|
| `Event.from_dict()` | Partial | New fields ignored by old `from_dict` | `from_dict` uses `data.get()` with defaults |
| `Event.to_dict()` | N/A | v3.0 always writes all fields | `to_dict` adds new keys gracefully |
| `CorrelationAnalyzer` | Yes | Only reads event_type, impact_level, outcome_tracking | No change needed |
| `DriftDetector` | Yes | Reads event_date, impact_level | No change needed |
| YAML parsers | Yes | Unknown keys are ignored by default | Standard YAML behavior |

**Key Design Decision**: New fields MUST use `data.get()` with defaults in `from_dict`. This ensures v2.0 files without these fields deserialize correctly as v3.0 objects with default values.

### 3.3 Logical Model: EventContract

```python
@dataclass
class ImpactRecord:
    """Single entity impact within a contract."""

    entity_id: str              # thesis or position ID
    entity_type: str            # "thesis" | "position"
    impact_score: float         # 0.0-1.0
    impact_direction: str       # "positive" | "negative" | "neutral"
    confidence: float = 0.5     # confidence in this impact assessment
    assessed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        d = {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "impact_score": self.impact_score,
            "impact_direction": self.impact_direction,
            "confidence": self.confidence,
        }
        if self.assessed_at is not None:
            d["assessed_at"] = self.assessed_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ImpactRecord:
        assessed = data.get("assessed_at")
        return cls(
            entity_id=data["entity_id"],
            entity_type=data["entity_type"],
            impact_score=float(data.get("impact_score", 0.5)),
            impact_direction=data.get("impact_direction", "neutral"),
            confidence=float(data.get("confidence", 0.5)),
            assessed_at=datetime.fromisoformat(assessed) if assessed else None,
        )


@dataclass
class EventContract(BaseSchema):
    """Links an Event to its affected theses and positions.

    Projection model: rebuildable from Event + PropagationEdge data.
    """

    schema_version: str = "1.0"

    # --- Event Link ---
    event_id: str = ""

    # --- Affected Entities ---
    affected_theses: list[str] = field(default_factory=list)     # thesis IDs
    affected_positions: list[str] = field(default_factory=list)  # position IDs

    # --- Impact Details ---
    impact_records: list[ImpactRecord] = field(default_factory=list)
    aggregate_impact: float = 0.0     # weighted sum of impacts
    propagation_depth: int = 0        # max hops from event

    # --- Lifecycle ---
    settled_at: Optional[datetime] = None
    settlement_reason: str = ""       # "expired" | "manual" | "contradicted"

    # --- Rebuild Metadata ---
    last_rebuilt_at: Optional[datetime] = None
    edge_count: int = 0               # number of edges in rebuild

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "event_id": self.event_id,
            "affected_theses": self.affected_theses,
            "affected_positions": self.affected_positions,
            "impact_records": [ir.to_dict() for ir in self.impact_records],
            "aggregate_impact": self.aggregate_impact,
            "propagation_depth": self.propagation_depth,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
            "settlement_reason": self.settlement_reason,
            "last_rebuilt_at": self.last_rebuilt_at.isoformat() if self.last_rebuilt_at else None,
            "edge_count": self.edge_count,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> EventContract:
        base = cls.base_from_dict(data)
        settled = data.get("settled_at")
        rebuilt = data.get("last_rebuilt_at")
        return cls(
            **base,
            event_id=data.get("event_id", ""),
            affected_theses=data.get("affected_theses", []),
            affected_positions=data.get("affected_positions", []),
            impact_records=[ImpactRecord.from_dict(ir) for ir in data.get("impact_records", [])],
            aggregate_impact=float(data.get("aggregate_impact", 0.0)),
            propagation_depth=int(data.get("propagation_depth", 0)),
            settled_at=datetime.fromisoformat(settled) if settled else None,
            settlement_reason=data.get("settlement_reason", ""),
            last_rebuilt_at=datetime.fromisoformat(rebuilt) if rebuilt else None,
            edge_count=int(data.get("edge_count", 0)),
        )
```

**Why EventContract is a standalone schema (not embedded in Event)**:

1. **Separation of concerns**: Event captures "what happened"; EventContract captures "what it affected"
2. **Independent lifecycle**: A contract can be settled/rebuilt without modifying the original Event
3. **Projection model**: EventContract is rebuildable from Event + PropagationEdge (as required by RFC)
4. **Storage efficiency**: Event files stay small; contracts grow with impact detail

### 3.4 Logical Model: PropagationEdge

```python
@dataclass
class PropagationEdge(BaseSchema):
    """Directed graph edge: source -> target with weight and decay.

    Source types: Event, Thesis
    Target types: Thesis, Position

    Valid edge patterns:
      Event -> Thesis   (event influences thesis)
      Event -> Position (event directly impacts position)
      Thesis -> Position (thesis validates/explains position)
      Thesis -> Thesis  (thesis evolves from another thesis)
    """

    schema_version: str = "1.0"

    # --- Graph Structure ---
    source_id: str = ""        # Event.id or Thesis.id
    source_type: str = ""      # "event" | "thesis"
    target_id: str = ""        # Thesis.id or Position.id
    target_type: str = ""      # "thesis" | "position"

    # --- Edge Properties ---
    weight: float = 0.5        # 0.0-1.0, influence strength
    decay_rate: float = 0.1    # per-day decay
    edge_type: str = "influence"  # "influence" | "evolution" | "contradiction"

    # --- Temporal ---
    effective_from: Optional[date] = None
    effective_until: Optional[date] = None
    last_weight_at: Optional[datetime] = None

    # --- Provenance ---
    detection_method: str = ""  # "rule_based" | "manual" | "inferred"
    confidence: float = 0.5

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "source_id": self.source_id,
            "source_type": self.source_type,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "weight": self.weight,
            "decay_rate": self.decay_rate,
            "edge_type": self.edge_type,
            "effective_from": self.effective_from.isoformat() if self.effective_from else None,
            "effective_until": self.effective_until.isoformat() if self.effective_until else None,
            "last_weight_at": self.last_weight_at.isoformat() if self.last_weight_at else None,
            "detection_method": self.detection_method,
            "confidence": self.confidence,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict) -> PropagationEdge:
        base = cls.base_from_dict(data)
        eff_from = data.get("effective_from")
        eff_until = data.get("effective_until")
        last_w = data.get("last_weight_at")
        return cls(
            **base,
            source_id=data.get("source_id", ""),
            source_type=data.get("source_type", ""),
            target_id=data.get("target_id", ""),
            target_type=data.get("target_type", ""),
            weight=float(data.get("weight", 0.5)),
            decay_rate=float(data.get("decay_rate", 0.1)),
            edge_type=data.get("edge_type", "influence"),
            effective_from=date.fromisoformat(eff_from) if eff_from else None,
            effective_until=date.fromisoformat(eff_until) if eff_until else None,
            last_weight_at=datetime.fromisoformat(last_w) if last_w else None,
            detection_method=data.get("detection_method", ""),
            confidence=float(data.get("confidence", 0.5)),
        )
```

**Edge validity constraints** (enforced at application layer):

| source_type | target_type | edge_type | Valid? |
|-------------|-------------|-----------|--------|
| event | thesis | influence | Yes |
| event | position | influence | Yes |
| thesis | position | influence | Yes |
| thesis | thesis | evolution | Yes |
| thesis | thesis | contradiction | Yes |
| position | * | * | No (positions don't propagate) |

---

## 4. Storage Strategy for Propagation Graphs

### 4.1 Storage Options Evaluated

**Option A: Adjacency List (embedded in EventContract)**

```
EventContract:
  event_id: "evt-001"
  affected_theses: ["thesis-A", "thesis-B"]
  affected_positions: ["pos-X"]
  edges:
    - {source: "evt-001", target: "thesis-A", weight: 0.8}
    - {source: "evt-001", target: "thesis-B", weight: 0.6}
    - {source: "thesis-A", target: "pos-X", weight: 0.7}
```

Pros: Compact, single file per event, easy to serialize
Cons: Duplicate edges if multiple contracts share edges, harder to query cross-event graphs

**Option B: Edge List (separate PropagationEdge files)**

```
edges/
  edge-001.yaml  # Event->Thesis
  edge-002.yaml  # Event->Thesis
  edge-003.yaml  # Thesis->Position
```

Pros: No duplication, easy to query all edges, natural graph representation
Cons: Many small files, cross-file joins needed

**Option C: Hybrid (recommended)**

- EventContract stores adjacency list for quick per-event queries
- PropagationEdge stored as independent YAML files for cross-event queries
- EventContract is rebuildable from PropagationEdge files (projection model)

### 4.2 Recommended: Hybrid Storage

```
research/
  events/
    evt-001.yaml          # Event v3.0
    evt-002.yaml
  contracts/
    ctr-001.yaml          # EventContract (adjacency list)
    ctr-002.yaml
  edges/
    edge-001.yaml         # PropagationEdge (independent)
    edge-002.yaml
    edge-003.yaml
```

**Rationale**:
- EventContract provides fast per-event lookups without scanning all edges
- PropagationEdge files enable cross-event graph queries (e.g., "all edges targeting thesis-A")
- EventContract is rebuildable from Edge files (deterministic projection)
- Consistent with P0-P2 file-per-entity pattern

### 4.3 Graph In-Memory Model

At query time, edges are loaded into an in-memory adjacency list:

```python
@dataclass
class PropagationGraph:
    """In-memory graph for traversal queries."""

    # Adjacency: node_id -> list of outgoing edges
    outgoing: dict[str, list[PropagationEdge]] = field(default_factory=dict)
    # Reverse: node_id -> list of incoming edges
    incoming: dict[str, list[PropagationEdge]] = field(default_factory=dict)
    # Node registry: node_id -> node_type
    node_types: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_edges(cls, edges: list[PropagationEdge]) -> PropagationGraph:
        graph = cls()
        for edge in edges:
            graph.outgoing.setdefault(edge.source_id, []).append(edge)
            graph.incoming.setdefault(edge.target_id, []).append(edge)
            graph.node_types[edge.source_id] = edge.source_type
            graph.node_types[edge.target_id] = edge.target_type
        return graph
```

---

## 5. Query Patterns for Event Impact Analysis

### 5.1 Query Pattern 1: Event Downstream Impact

**Purpose**: Find all theses and positions affected by a specific event.

```python
def query_event_impact(graph: PropagationGraph, event_id: str) -> dict:
    """BFS from event node, collecting all reachable theses/positions."""
    visited = set()
    queue = [(event_id, 0, 1.0)]  # (node_id, depth, cumulative_weight)
    impacts = {"theses": {}, "positions": {}}

    while queue:
        node_id, depth, cum_weight = queue.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)

        for edge in graph.outgoing.get(node_id, []):
            effective_weight = cum_weight * edge.weight * decay(edge.decay_rate, edge)
            target_type = graph.node_types.get(edge.target_id, "unknown")

            if target_type == "thesis":
                impacts["theses"][edge.target_id] = max(
                    impacts["theses"].get(edge.target_id, 0),
                    effective_weight
                )
            elif target_type == "position":
                impacts["positions"][edge.target_id] = max(
                    impacts["positions"].get(edge.target_id, 0),
                    effective_weight
                )

            queue.append((edge.target_id, depth + 1, effective_weight))

    return impacts
```

### 5.2 Query Pattern 2: Position Impact Source

**Purpose**: Find all events that influenced a specific position.

```python
def query_position_sources(graph: PropagationGraph, position_id: str) -> list[dict]:
    """Reverse BFS from position, finding all contributing events."""
    visited = set()
    queue = [(position_id, 0)]
    sources = []

    while queue:
        node_id, depth = queue.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)

        for edge in graph.incoming.get(node_id, []):
            source_type = graph.node_types.get(edge.source_id, "unknown")
            sources.append({
                "event_id" if source_type == "event" else "thesis_id": edge.source_id,
                "source_type": source_type,
                "weight": edge.weight,
                "depth": depth,
            })
            queue.append((edge.source_id, depth + 1))

    return sources
```

### 5.3 Query Pattern 3: Graph Cycle Detection

**Purpose**: Prevent circular references before creating new edges.

```python
def has_cycle_after_addition(
    graph: PropagationGraph,
    new_source: str,
    new_target: str
) -> bool:
    """Check if adding edge source->target would create a cycle.

    Uses DFS from new_target; if we reach new_source, cycle exists.
    """
    visited = set()
    stack = [new_target]

    while stack:
        node_id = stack.pop()
        if node_id == new_source:
            return True
        if node_id in visited:
            continue
        visited.add(node_id)
        for edge in graph.outgoing.get(node_id, []):
            stack.append(edge.target_id)

    return False
```

### 5.4 Query Pattern 4: Decay-Weighted Impact at Time T

**Purpose**: Calculate effective impact at a specific point in time.

```python
import math

def effective_weight(edge: PropagationEdge, at_date: date) -> float:
    """Calculate weight after temporal decay."""
    if edge.effective_from is None:
        return edge.weight

    days_elapsed = (at_date - edge.effective_from).days
    if days_elapsed < 0:
        return 0.0  # not yet effective

    decay_factor = math.exp(-edge.decay_rate * days_elapsed)
    return edge.weight * decay_factor
```

### 5.5 Query Pattern 5: Aggregate Contract Rebuild

**Purpose**: Rebuild EventContract from raw edges (deterministic projection).

```python
def rebuild_contract(
    event: Event,
    edges: list[PropagationEdge],
) -> EventContract:
    """Deterministic projection: EventContract from Event + Edges.

    MUST produce identical output given identical inputs.
    """
    event_edges = [e for e in edges if e.source_id == event.id]

    affected_theses = []
    affected_positions = []
    impact_records = []
    max_depth = 0

    # BFS to collect all downstream entities
    visited = set()
    queue = [(event.id, 0, 1.0)]

    while queue:
        node_id, depth, cum_weight = queue.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)
        max_depth = max(max_depth, depth)

        for edge in [e for e in edges if e.source_id == node_id]:
            effective = cum_weight * edge.weight
            if edge.target_type == "thesis" and edge.target_id not in affected_theses:
                affected_theses.append(edge.target_id)
                impact_records.append(ImpactRecord(
                    entity_id=edge.target_id,
                    entity_type="thesis",
                    impact_score=effective,
                    impact_direction="positive" if effective > 0 else "negative",
                    confidence=edge.confidence,
                ))
            elif edge.target_type == "position" and edge.target_id not in affected_positions:
                affected_positions.append(edge.target_id)
                impact_records.append(ImpactRecord(
                    entity_id=edge.target_id,
                    entity_type="position",
                    impact_score=effective,
                    impact_direction="positive" if effective > 0 else "negative",
                    confidence=edge.confidence,
                ))
            queue.append((edge.target_id, depth + 1, effective))

    aggregate = sum(ir.impact_score for ir in impact_records) / len(impact_records) if impact_records else 0.0

    return EventContract(
        id=f"ctr-{event.id}",
        event_id=event.id,
        affected_theses=affected_theses,
        affected_positions=affected_positions,
        impact_records=impact_records,
        aggregate_impact=aggregate,
        propagation_depth=max_depth,
        edge_count=len(event_edges),
        last_rebuilt_at=datetime.now(CST),
    )
```

---

## 6. Data Migration Strategy (Lazy Upcast Compatibility)

### 6.1 Migration Principles

Following ADR-005 (Weak Schema + Lazy Upcast):

1. **No migration scripts**: Old files are read as-is; new fields get defaults
2. **Write latest**: All writes produce v3.0 format
3. **Schema version bump**: `schema_version: "2.0"` -> `"3.0"` on Event
4. **New files only**: EventContract and PropagationEdge are new schemas (no migration needed)

### 6.2 Event v2.0 -> v3.0 Upgrade Path

```
Read path:
  YAML file (schema_version: "2.0")
    -> Event.from_dict(data)
    -> data.get("confidence", 0.5)     # new field, default 0.5
    -> data.get("severity", 0.5)       # new field, default 0.5
    -> data.get("decay_rate", 0.1)     # new field, default 0.1
    -> data.get("source", "manual")    # new field, default "manual"
    -> data.get("propagation_state", "detected")  # new field, default "detected"
    -> Event object (v3.0 in memory)

Write path:
  Event object (v3.0 in memory)
    -> event.to_dict()
    -> includes all v3.0 fields
    -> schema_version: "3.0"
    -> YAML file (schema_version: "3.0")
```

### 6.3 New Schema File Layout

```
research/
  events/
    evt-001.yaml    # Event (may be v2.0 or v3.0)
    evt-002.yaml    # Event v3.0
  contracts/         # NEW directory for P3
    ctr-evt-001.yaml
  edges/             # NEW directory for P3
    edge-001.yaml
    edge-002.yaml
```

### 6.4 Backward Compatibility Matrix

| Scenario | Behavior | Risk |
|----------|----------|------|
| v2.0 consumer reads v3.0 Event | Ignores new fields, works normally | Low |
| v3.0 consumer reads v2.0 Event | New fields get defaults, works normally | Low |
| v3.0 consumer reads missing EventContract | Returns empty contract (no affected entities) | Low |
| v3.0 consumer reads missing PropagationEdge | Empty graph, no traversal results | Low |
| P2 CorrelationAnalyzer reads v3.0 Event | Unchanged (reads event_type, impact_level, outcome_tracking) | None |

---

## 7. Indexing and Performance for Graph Traversals

### 7.1 In-Memory Index Strategy

Since SYNAPSE uses file-based YAML storage (no database), indexing is done at load time:

```python
@dataclass
class GraphIndex:
    """Pre-computed indices for fast graph queries."""

    # Primary indices
    edges_by_source: dict[str, list[PropagationEdge]] = field(default_factory=dict)
    edges_by_target: dict[str, list[PropagationEdge]] = field(default_factory=dict)

    # Secondary indices
    edges_by_type: dict[str, list[PropagationEdge]] = field(default_factory=dict)
    events_by_type: dict[str, list[str]] = field(default_factory=dict)  # event_type -> event_ids
    contracts_by_event: dict[str, str] = field(default_factory=dict)    # event_id -> contract_id

    # Aggregates
    total_edges: int = 0
    total_contracts: int = 0
    max_depth: int = 0

    @classmethod
    def build(cls, edges: list[PropagationEdge], contracts: list[EventContract]) -> GraphIndex:
        idx = cls()
        for edge in edges:
            idx.edges_by_source.setdefault(edge.source_id, []).append(edge)
            idx.edges_by_target.setdefault(edge.target_id, []).append(edge)
            idx.edges_by_type.setdefault(edge.edge_type, []).append(edge)
        for contract in contracts:
            idx.contracts_by_event[contract.event_id] = contract.id
        idx.total_edges = len(edges)
        idx.total_contracts = len(contracts)
        return idx
```

### 7.2 Performance Characteristics

| Operation | Without Index | With Index | Notes |
|-----------|---------------|------------|-------|
| Find edges by source | O(E) scan | O(1) lookup | E = total edges |
| Find edges by target | O(E) scan | O(1) lookup | |
| BFS from event | O(E + V) | O(degree * depth) | V = vertices |
| Cycle detection | O(V + E) | O(degree * depth) | DFS from target |
| Contract rebuild | O(E) scan | O(degree * depth) | BFS + filter |

**Expected performance for SYNAPSE scale**:
- 200 events/year, 2000 edges/year
- In-memory graph: ~200KB (edges) + ~50KB (indices) = ~250KB
- BFS traversal: < 1ms (CPU-bound, no I/O)
- Full graph load from YAML: ~50ms (file I/O dominant)

### 7.3 Caching Strategy

```python
class GraphCache:
    """LRU cache for graph queries, invalidated on edge writes."""

    def __init__(self, max_size: int = 100):
        self._cache: dict[str, Any] = {}
        self._max_size = max_size
        self._version: int = 0  # incremented on write

    def get(self, key: str, version: int) -> Any:
        if version != self._version:
            return None  # cache invalidated
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        if len(self._cache) >= self._max_size:
            # evict oldest
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = value

    def invalidate(self) -> None:
        self._version += 1
        self._cache.clear()
```

### 7.4 File I/O Optimization

For graphs with many edges, batch file reads:

```python
def load_all_edges(edges_dir: Path) -> list[PropagationEdge]:
    """Load all edge files in a single directory scan."""
    edges = []
    for edge_file in sorted(edges_dir.glob("edge-*.yaml")):
        with open(edge_file) as f:
            data = yaml.safe_load(f)
            edges.append(PropagationEdge.from_dict(data))
    return edges
```

**Optimization**: If edge count exceeds 500, consider a single `edges-manifest.yaml` listing all edge IDs to avoid directory listing overhead.

---

## 8. Integration Architecture

### 8.1 Integration with P0-P2 Components

| Component | Integration Point | Data Flow |
|-----------|-------------------|-----------|
| Event (v2.0) | Extend to v3.0 | Add propagation fields |
| Thesis | Add `event_influence` field | List of event_ids that shaped thesis |
| Position | Add `event_impact` field | List of (event_id, impact_score) |
| Decision | Read `attention_origin` | EVENT_ATTENTION triggers propagation |
| Review | Add `event_id` field | Link review to triggering event |
| CorrelationAnalyzer | Feed Event v3.0 | Read event_type, impact_level |
| DriftDetector | Feed propagation_state | Detect event-induced drift |
| BiasDetector | Feed event source | Detect event-reaction bias |

### 8.2 New Integration Points

| P3 Component | Input | Output | Integration |
|--------------|-------|--------|-------------|
| Event Detection Engine | Market data | Event v3.0 | Writes to events/ |
| Event Propagation Builder | Event + existing graph | PropagationEdge | Writes to edges/ |
| EventContract Projector | Event + edges | EventContract | Writes to contracts/ |
| Event Impact Analyzer | Contract + edges | Impact report | Read-only query |
| Event CLI | User commands | Event/Contract/Edge | CLI subcommands |

---

## 9. Recommendations

### 9.1 Architecture Approach

1. **Hybrid storage**: EventContract (adjacency list) + PropagationEdge (edge list) + in-memory graph
2. **Lazy Upcast**: Event v3.0 extends v2.0 with additive fields only
3. **Projection model**: EventContract is deterministic rebuild from Event + Edges
4. **In-memory indexing**: Build indices at query time, cache with version-based invalidation

### 9.2 Technology Stack

- **Storage**: YAML files (consistent with P0-P2)
- **Graph model**: In-memory adjacency list (no external graph database)
- **Query**: Python BFS/DFS with cycle detection
- **Migration**: None (Lazy Upcast)

### 9.3 Implementation Phases

| Phase | Deliverable | Dependencies |
|-------|-------------|--------------|
| P3a | Event v3.0 schema + migration | None |
| P3b | PropagationEdge schema + storage | P3a |
| P3c | EventContract schema + projector | P3a, P3b |
| P3d | Graph traversal + cycle detection | P3b |
| P3e | Event Detection Engine | P3a |
| P3f | Propagation Builder + Impact Analyzer | P3b, P3c, P3d |
| P3g | CLI subcommands | P3e, P3f |

### 9.4 Monitoring and Observability

| Metric | Description | Threshold |
|--------|-------------|-----------|
| `graph_load_time_ms` | Time to load edges into memory | < 100ms |
| `traversal_depth_max` | Maximum BFS depth observed | < 10 |
| `cycle_detection_count` | Cycles prevented | Log all |
| `contract_rebuild_count` | Contracts rebuilt from projection | Log all |
| `edge_count_total` | Total edges in system | Alert if > 5000 |
| `propagation_state_distribution` | Events by state | Log daily |

---

## Appendix A: Schema Version History

| Schema | P1 Version | P2 Version | P3 Version | Change |
|--------|-----------|-----------|-----------|--------|
| Event | 1.0 | 2.0 | 3.0 | +propagation fields |
| EventContract | -- | -- | 1.0 | New schema |
| PropagationEdge | -- | -- | 1.0 | New schema |
| All others | 1.0 | 1.0 | 1.0 | Unchanged |

## Appendix B: File Naming Conventions

```
events/evt-{uuid}.yaml         # Event v3.0
contracts/ctr-evt-{uuid}.yaml  # EventContract (ID derived from event)
edges/edge-{uuid}.yaml         # PropagationEdge
```

## Appendix C: Determinism Contract

EventContract rebuild MUST be deterministic:
- Same Event + same PropagationEdge set -> identical EventContract
- Edge ordering does not affect final impact_scores (uses max aggregation)
- Timestamp fields (last_rebuilt_at) excluded from determinism check
- Implementation: sort edges by source_id, target_id before BFS
