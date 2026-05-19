# System Architect Analysis: P3 Event-Driven Research Contracts

## 1. Executive Summary

P3 introduces event-driven research contracts to SYNAPSE's research memory layer, extending the existing 5-layer architecture with event lifecycle management, propagation graphs, and pluggable detection engines. This analysis defines the technical architecture for Component #8-#13, ensuring backward compatibility with P0-P2 schemas while enabling deterministic event propagation through a directed acyclic graph (DAG).

**Key Architectural Decisions:**
- Event lifecycle follows a 4-state machine: detected → propagating → settled → expired
- Propagation graph uses adjacency list representation with topological sort for deterministic execution
- Event detection employs pluggable detector pattern with rule-based engines
- All event contracts are projections rebuildable from raw events
- Configuration uses YAML-based type registry with decay parameters

---

## 2. Event Lifecycle State Machine

### 2.1 State Definitions

| State | Description | Entry Conditions | Exit Conditions |
|-------|-------------|------------------|-----------------|
| `detected` | Event just detected, not yet analyzed | Detector fires | Propagation graph built |
| `propagating` | Event influence spreading through graph | Graph built, edges computed | All downstream impacts settled |
| `settled` | Event fully processed, impacts recorded | All downstream settled | Manual or timeout expiry |
| `expired` | Event past decay threshold, no longer active | Decay < threshold or manual | Terminal state |

### 2.2 State Machine Diagram

```
                          +-----------------+
                          |                 |
                  +-------+   detected      |
                  |       |                 |
                  |       +--------+--------+
                  |                |
                  |   [build_graph]
                  |                |
                  v                v
          +-------+-------+       |
          |               |       |
          |  propagating  |       |
          |               |       |
          +-------+-------+       |
                  |                |
    [all_downstream_settled]       |
                  |                |
                  v                v
          +-------+-------+       |
          |               |       |
          |   settled     |       |
          |               |       |
          +-------+-------+       |
                  |                |
      [decay < threshold]         |
          or [manual]             |
                  |                |
                  v                v
          +-------+-------+       |
          |               |       |
          |   expired     |<------+
          |               |  [decay < threshold]
          +---------------+
                  ^
                  |
          [timeout from propagating]
          (stuck protection)
```

### 2.3 State Transition Rules

```python
# State transition table
TRANSITIONS = {
    "detected": {
        "propagating": "build_propagation_graph()",
    },
    "propagating": {
        "settled": "all_downstream_settled()",
        "expired": "stuck_timeout_exceeded()",  # safety valve
    },
    "settled": {
        "expired": "decay_below_threshold() or manual_expire()",
    },
    "expired": {
        # Terminal state - no transitions out
    },
}
```

### 2.4 State Machine Implementation

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable

class PropagationState(str, Enum):
    DETECTED = "detected"
    PROPAGATING = "propagating"
    SETTLED = "settled"
    EXPIRED = "expired"

@dataclass
class StateTransition:
    from_state: PropagationState
    to_state: PropagationState
    guard: Callable[["EventContract"], bool]
    action: Optional[Callable[["EventContract"], None]] = None

class EventStateMachine:
    """Deterministic state machine for event lifecycle."""

    def __init__(self):
        self.transitions: list[StateTransition] = []
        self._register_default_transitions()

    def _register_default_transitions(self):
        self.transitions = [
            StateTransition(
                from_state=PropagationState.DETECTED,
                to_state=PropagationState.PROPAGATING,
                guard=lambda e: e.propagation_graph is not None,
            ),
            StateTransition(
                from_state=PropagationState.PROPAGATING,
                to_state=PropagationState.SETTLED,
                guard=lambda e: e.all_downstream_settled(),
            ),
            StateTransition(
                from_state=PropagationState.PROPAGATING,
                to_state=PropagationState.EXPIRED,
                guard=lambda e: e.is_stuck_timeout_exceeded(),
            ),
            StateTransition(
                from_state=PropagationState.SETTLED,
                to_state=PropagationState.EXPIRED,
                guard=lambda e: e.decay_below_threshold() or e.manual_expire_requested,
            ),
        ]

    def transition(self, event: "EventContract") -> PropagationState:
        """Execute valid transition for event."""
        for t in self.transitions:
            if t.from_state == event.propagation_state and t.guard(event):
                if t.action:
                    t.action(event)
                return t.to_state
        return event.propagation_state  # No valid transition
```

### 2.5 Stuck State Protection

Events in `propagating` state MUST NOT remain indefinitely. The system enforces a stuck timeout:

```python
STUCK_TIMEOUT_DAYS = 7  # Configurable per event type

def is_stuck_timeout_exceeded(self) -> bool:
    """Check if event has been propagating too long."""
    if self.propagation_state != PropagationState.PROPAGATING:
        return False
    elapsed = (datetime.now(CST) - self.propagated_at).days
    return elapsed > self.stuck_timeout_days
```

---

## 3. Propagation Graph Architecture

### 3.1 Graph Structure

The propagation graph is a **directed acyclic graph (DAG)** representing event → thesis → position influence paths.

```
                    +-----------+
                    |   Event   |
                    | (source)  |
                    +-----+-----+
                          |
            +-------------+-------------+
            |             |             |
            v             v             v
      +-----+-----+ +----+----+ +-----+-----+
      |  Thesis   | | Thesis  | |  Thesis   |
      |  (A)      | | (B)     | |  (C)      |
      +-----+-----+ +----+----+ +-----+-----+
            |             |             |
            v             v             v
      +-----+-----+ +----+----+ +-----+-----+
      | Position  | |Position | | Position  |
      |  (X)      | | (Y)     | |  (Z)      |
      +-----------+ +---------+ +-----------+
```

### 3.2 Adjacency List Representation

```python
from dataclasses import dataclass, field

@dataclass
class PropagationEdge:
    """Directed edge in propagation graph."""
    source_id: str          # event or thesis ID
    target_id: str          # thesis or position ID
    weight: float           # 0.0-1.0, impact strength
    decay: float            # per-day decay factor
    edge_type: str          # "event_to_thesis" | "thesis_to_position"
    created_at: datetime = field(default_factory=lambda: datetime.now(CST))

@dataclass
class PropagationGraph:
    """DAG for event influence propagation."""
    event_id: str
    edges: list[PropagationEdge] = field(default_factory=list)
    topological_order: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "edges": [self._edge_to_dict(e) for e in self.edges],
            "topological_order": self.topological_order,
        }

    def _edge_to_dict(self, edge: PropagationEdge) -> dict:
        return {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "weight": edge.weight,
            "decay": edge.decay,
            "edge_type": edge.edge_type,
            "created_at": edge.created_at.isoformat(),
        }
```

### 3.3 Cycle Detection Algorithm

The system MUST detect and prevent circular references before graph construction.

```python
def detect_cycles(self) -> list[list[str]]:
    """Detect cycles using Tarjan's algorithm.
    
    Returns list of cycles found. Each cycle is a list of node IDs.
    Raises ValueError if cycle detected during graph construction.
    """
    index_counter = [0]
    stack = []
    lowlink = {}
    index = {}
    on_stack = {}
    cycles = []

    def strongconnect(v):
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in self._get_neighbors(v):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w, False):
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            cycle = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                cycle.append(w)
                if w == v:
                    break
            if len(cycle) > 1:
                cycles.append(cycle)

    for node in self._get_all_nodes():
        if node not in index:
            strongconnect(node)

    return cycles
```

### 3.4 Topological Sort for Deterministic Propagation

```python
def topological_sort(self) -> list[str]:
    """Compute topological order for deterministic propagation.
    
    Returns nodes in dependency order (sources before targets).
    Raises ValueError if graph contains cycles.
    """
    # Detect cycles first
    cycles = self.detect_cycles()
    if cycles:
        raise ValueError(f"Cycle detected: {cycles}")

    # Kahn's algorithm for topological sort
    in_degree = {node: 0 for node in self._get_all_nodes()}
    for edge in self.edges:
        in_degree[edge.target_id] = in_degree.get(edge.target_id, 0) + 1

    queue = [node for node, deg in in_degree.items() if deg == 0]
    result = []

    while queue:
        # Sort for deterministic order
        queue.sort()
        node = queue.pop(0)
        result.append(node)

        for neighbor in self._get_neighbors(node):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(self._get_all_nodes()):
        raise ValueError("Graph contains cycles (inconsistent in-degree)")

    self.topological_order = result
    return result
```

### 3.5 Graph Construction from Event Relationships

```python
def build_propagation_graph(
    event: Event,
    theses: list[Thesis],
    positions: list[Position],
) -> PropagationGraph:
    """Build propagation graph from event and related entities.
    
    Links are established via:
    1. Event.related_tickers -> Thesis.related_securities.ticker
    2. Thesis.id -> Position.linked_thesis_id
    """
    graph = PropagationGraph(event_id=event.id)
    
    # Build ticker -> thesis mapping
    ticker_theses: dict[str, list[Thesis]] = {}
    for thesis in theses:
        for sec in thesis.related_securities:
            ticker_theses.setdefault(sec.ticker, []).append(thesis)

    # Build thesis -> position mapping
    thesis_positions: dict[str, list[Position]] = {}
    for pos in positions:
        if pos.linked_thesis_id:
            thesis_positions.setdefault(pos.linked_thesis_id, []).append(pos)

    # Create event -> thesis edges
    for ticker in event.related_tickers:
        for thesis in ticker_theses.get(ticker, []):
            weight = _compute_event_thesis_weight(event, thesis)
            graph.edges.append(PropagationEdge(
                source_id=event.id,
                target_id=thesis.id,
                weight=weight,
                decay=event.decay_rate,
                edge_type="event_to_thesis",
            ))

    # Create thesis -> position edges
    for thesis in theses:
        for pos in thesis_positions.get(thesis.id, []):
            weight = 1.0  # Direct link, full weight
            graph.edges.append(PropagationEdge(
                source_id=thesis.id,
                target_id=pos.id,
                weight=weight,
                decay=0.0,  # Position doesn't decay
                edge_type="thesis_to_position",
            ))

    # Compute topological order
    graph.topological_sort()
    
    return graph
```

### 3.6 Graph Storage

Graphs are stored as part of EventContract projections, rebuildable from raw events:

```
workspace/
  events/
    {date}/
      event_{id}/
        meta.yaml           # Event schema
        contract.yaml       # EventContract projection
        propagation.yaml    # PropagationGraph projection
```

---

## 4. Event Detection Engine Design

### 4.1 Pluggable Detector Pattern

The detection engine uses a strategy pattern for extensibility.

```python
from abc import ABC, abstractmethod

class EventDetector(ABC):
    """Abstract base for event detectors."""
    
    @abstractmethod
    def detect(self, data: dict) -> list[Event]:
        """Detect events from input data."""
        pass
    
    @abstractmethod
    def event_type(self) -> EventType:
        """Return the event type this detector handles."""
        pass
    
    @abstractmethod
    def confidence_threshold(self) -> float:
        """Minimum confidence for detection."""
        pass

class RuleBasedDetector(EventDetector):
    """Rule-based detector for structured data."""
    
    def __init__(self, rules: list[DetectionRule]):
        self.rules = rules
    
    def detect(self, data: dict) -> list[Event]:
        events = []
        for rule in self.rules:
            if rule.matches(data):
                events.append(rule.to_event(data))
        return events
```

### 4.2 Detector Registry

```python
from typing import Dict, Type

class DetectorRegistry:
    """Registry for event detectors."""
    
    _detectors: Dict[EventType, Type[EventDetector]] = {}
    
    @classmethod
    def register(cls, event_type: EventType, detector_class: Type[EventDetector]):
        """Register a detector for an event type."""
        cls._detectors[event_type] = detector_class
    
    @classmethod
    def get(cls, event_type: EventType) -> EventDetector:
        """Get detector instance for event type."""
        detector_class = cls._detectors.get(event_type)
        if not detector_class:
            raise ValueError(f"No detector registered for {event_type}")
        return detector_class()
    
    @classmethod
    def detect_all(cls, data: dict) -> list[Event]:
        """Run all registered detectors."""
        events = []
        for event_type, detector_class in cls._detectors.items():
            detector = detector_class()
            events.extend(detector.detect(data))
        return events

# Registration via decorator
@DetectorRegistry.register(EventType.EARNINGS)
class EarningsDetector(RuleBasedDetector):
    """Detect earnings announcements."""
    pass
```

### 4.3 Event Deduplication

```python
def deduplicate_events(events: list[Event]) -> list[Event]:
    """Deduplicate events using configurable merge rules.
    
    Deduplication strategy:
    1. Same event_type + same related_tickers + overlapping date window
    2. Merge: keep highest confidence, union tickers
    """
    merged: dict[str, Event] = {}
    
    for event in events:
        key = _deduplication_key(event)
        
        if key in merged:
            existing = merged[key]
            # Merge strategy: keep higher confidence
            if event.confidence > existing.confidence:
                merged[key] = _merge_events(event, existing)
            else:
                merged[key] = _merge_events(existing, event)
        else:
            merged[key] = event
    
    return list(merged.values())

def _deduplication_key(event: Event) -> str:
    """Generate deduplication key."""
    tickers = sorted(event.related_tickers)
    return f"{event.event_type.value}:{','.join(tickers)}"
```

### 4.4 Detection Flow

```
                    +-----------------+
                    |  Raw Data Input |
                    | (YAML/JSON)     |
                    +--------+--------+
                             |
                             v
                    +--------+--------+
                    | Detector        |
                    | Registry        |
                    +--------+--------+
                             |
            +----------------+----------------+
            |                |                |
            v                v                v
    +-------+-------+ +-----+-----+ +-------+-------+
    | Earnings      | | Policy    | | Sentiment     |
    | Detector      | | Detector  | | Detector      |
    +-------+-------+ +-----+-----+ +-------+-------+
            |                |                |
            +----------------+----------------+
                             |
                             v
                    +--------+--------+
                    | Event           |
                    | Deduplication   |
                    +--------+--------+
                             |
                             v
                    +--------+--------+
                    | Confidence      |
                    | Filtering       |
                    | (>= threshold)  |
                    +--------+--------+
                             |
                             v
                    +--------+--------+
                    | Event Schema    |
                    | Construction    |
                    +-----------------+
```

---

## 5. Integration with Existing 5-Layer Architecture

### 5.1 Layer Mapping

| Layer | P0-P2 Components | P3 Extensions |
|-------|-----------------|---------------|
| **L1: Data** | data/loader, data/validator | Event data sources |
| **L2: Schema** | 11 schemas (Event v2) | Event v3, EventContract, PropagationEdge |
| **L3: Analytics** | 7 analyzers (Correlation, Drift, Bias) | EventImpactAnalyzer, PropagationAnalyzer |
| **L4: Projection** | position_rebuilder, watchlist_generator | EventContractBuilder, PropagationGraphBuilder |
| **L5: Workflow** | daily_research, decision_flow, review_flow | event_detection_flow, event_propagation_flow |

### 5.2 Schema Extension (Lazy Upcast)

Event schema v3.0 extends existing v2.0 with backward compatibility:

```python
@dataclass
class Event(BaseSchema):
    """Market event of interest — v3.0 with propagation support."""
    
    schema_version: str = "3.0"  # Updated from 2.0
    
    # --- Existing v2.0 fields (unchanged) ---
    event_type: EventType = EventType.EARNINGS
    title: str = ""
    description: str = ""
    event_date: Optional[date] = None
    related_tickers: list[str] = field(default_factory=list)
    impact_level: ImpactLevel = ImpactLevel.UNKNOWN
    outcome_tracking: list[OutcomeRecord] = field(default_factory=list)
    linked_review_ids: list[str] = field(default_factory=list)
    calibration_score: Optional[float] = None
    
    # --- New v3.0 fields (backward compatible) ---
    severity: float = 0.5          # 0.0-1.0
    confidence: float = 0.5        # 0.0-1.0
    decay_rate: float = 0.1        # per-day decay factor
    source: str = "manual"         # "data_feed" | "news" | "manual" | "ai_detected"
    propagation_state: PropagationState = PropagationState.DETECTED
    
    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            # v2.0 fields
            "event_type": self.event_type.value,
            "title": self.title,
            "description": self.description,
            "event_date": self.event_date.isoformat() if self.event_date else None,
            "related_tickers": self.related_tickers,
            "impact_level": self.impact_level.value,
            "outcome_tracking": [o.to_dict() for o in self.outcome_tracking],
            "linked_review_ids": self.linked_review_ids,
            "calibration_score": self.calibration_score,
            # v3.0 fields
            "severity": self.severity,
            "confidence": self.confidence,
            "decay_rate": self.decay_rate,
            "source": self.source,
            "propagation_state": self.propagation_state.value,
        })
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> Event:
        base = cls.base_from_dict(data)
        return cls(
            **base,
            # v2.0 fields
            event_type=EventType(data.get("event_type", "earnings")),
            title=data.get("title", ""),
            description=data.get("description", ""),
            event_date=date.fromisoformat(data["event_date"]) if data.get("event_date") else None,
            related_tickers=data.get("related_tickers", []),
            impact_level=ImpactLevel(data.get("impact_level", "unknown")),
            outcome_tracking=[OutcomeRecord.from_dict(o) for o in data.get("outcome_tracking", [])],
            linked_review_ids=data.get("linked_review_ids", []),
            calibration_score=float(data["calibration_score"]) if data.get("calibration_score") is not None else None,
            # v3.0 fields (with defaults for v2.0 data)
            severity=float(data.get("severity", 0.5)),
            confidence=float(data.get("confidence", 0.5)),
            decay_rate=float(data.get("decay_rate", 0.1)),
            source=data.get("source", "manual"),
            propagation_state=PropagationState(data.get("propagation_state", "detected")),
        )
```

### 5.3 New Schema: EventContract

```python
@dataclass
class EventContract(BaseSchema):
    """Event propagation contract — projection from raw events."""
    
    schema_version: str = "1.0"
    
    # --- Core ---
    event_id: str
    affected_theses: list[str] = field(default_factory=list)
    affected_positions: list[str] = field(default_factory=list)
    impact_scores: dict[str, float] = field(default_factory=dict)
    propagation_path: list[str] = field(default_factory=list)
    
    # --- Lifecycle ---
    propagation_state: PropagationState = PropagationState.DETECTED
    propagated_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    
    # --- Decay ---
    current_decay: float = 1.0  # Starts at 1.0, decays over time
    decay_rate: float = 0.1
    
    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "event_id": self.event_id,
            "affected_theses": self.affected_theses,
            "affected_positions": self.affected_positions,
            "impact_scores": self.impact_scores,
            "propagation_path": self.propagation_path,
            "propagation_state": self.propagation_state.value,
            "propagated_at": self.propagated_at.isoformat() if self.propagated_at else None,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
            "expired_at": self.expired_at.isoformat() if self.expired_at else None,
            "current_decay": self.current_decay,
            "decay_rate": self.decay_rate,
        })
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> EventContract:
        base = cls.base_from_dict(data)
        return cls(
            **base,
            event_id=data["event_id"],
            affected_theses=data.get("affected_theses", []),
            affected_positions=data.get("affected_positions", []),
            impact_scores=data.get("impact_scores", {}),
            propagation_path=data.get("propagation_path", []),
            propagation_state=PropagationState(data.get("propagation_state", "detected")),
            propagated_at=datetime.fromisoformat(data["propagated_at"]) if data.get("propagated_at") else None,
            settled_at=datetime.fromisoformat(data["settled_at"]) if data.get("settled_at") else None,
            expired_at=datetime.fromisoformat(data["expired_at"]) if data.get("expired_at") else None,
            current_decay=float(data.get("current_decay", 1.0)),
            decay_rate=float(data.get("decay_rate", 0.1)),
        )
    
    def all_downstream_settled(self) -> bool:
        """Check if all downstream entities are settled."""
        # Implementation depends on propagation graph
        return len(self.affected_theses) == 0 and len(self.affected_positions) == 0
    
    def decay_below_threshold(self, threshold: float = 0.1) -> bool:
        """Check if decay has fallen below threshold."""
        return self.current_decay < threshold
    
    def is_stuck_timeout_exceeded(self, timeout_days: int = 7) -> bool:
        """Check if event has been propagating too long."""
        if self.propagation_state != PropagationState.PROPAGATING:
            return False
        if not self.propagated_at:
            return False
        elapsed = (datetime.now(CST) - self.propagated_at).days
        return elapsed > timeout_days
```

### 5.4 Analytics Integration

```python
# Integration with existing CorrelationAnalyzer
class EventImpactAnalyzer:
    """Quantify event impact on positions and theses."""
    
    def analyze(
        self,
        event: Event,
        contract: EventContract,
        positions: list[Position],
        reviews: list[Review],
    ) -> ImpactReport:
        """Compute impact metrics for an event."""
        # Before/after comparison
        before_state = self._capture_state(positions, contract.affected_positions)
        after_state = self._capture_state(positions, contract.affected_positions)
        
        # Risk-adjusted impact
        risk_adjusted = self._compute_risk_adjusted_impact(
            contract.impact_scores,
            before_state,
            after_state,
        )
        
        return ImpactReport(
            event_id=event.id,
            affected_count=len(contract.affected_theses) + len(contract.affected_positions),
            impact_scores=contract.impact_scores,
            risk_adjusted_scores=risk_adjusted,
        )
```

### 5.5 Projection Layer Extension

```python
class EventContractBuilder:
    """Build EventContract projections from raw events."""
    
    def build(
        self,
        event: Event,
        theses: list[Thesis],
        positions: list[Position],
    ) -> EventContract:
        """Build EventContract from event and related entities."""
        # Build propagation graph
        graph = build_propagation_graph(event, theses, positions)
        
        # Extract affected entities
        affected_theses = [e.target_id for e in graph.edges if e.edge_type == "event_to_thesis"]
        affected_positions = [e.target_id for e in graph.edges if e.edge_type == "thesis_to_position"]
        
        # Compute impact scores
        impact_scores = self._compute_impact_scores(graph)
        
        return EventContract(
            id=f"contract_{event.id}",
            event_id=event.id,
            affected_theses=affected_theses,
            affected_positions=affected_positions,
            impact_scores=impact_scores,
            propagation_path=graph.topological_order,
            propagation_state=PropagationState.DETECTED,
            decay_rate=event.decay_rate,
        )
```

---

## 6. Scalability Considerations

### 6.1 Event Volume Projections

| Scenario | Events/Day | Events/Month | Peak Events/Day |
|----------|-----------|--------------|-----------------|
| Conservative | 5-10 | 150-300 | 20 |
| Moderate | 20-50 | 600-1500 | 100 |
| High | 100-200 | 3000-6000 | 500 |

### 6.2 Graph Size Limits

```python
# Configuration for graph limits
GRAPH_LIMITS = {
    "max_nodes_per_graph": 100,      # Event + theses + positions
    "max_edges_per_graph": 200,      # Relationships
    "max_propagation_depth": 5,      # Event -> Thesis -> Position -> ...
    "max_concurrent_propagations": 10, # Parallel graph processing
}
```

### 6.3 Performance Optimization

**Adjacency List with Index:**
```python
class OptimizedPropagationGraph:
    """Graph with O(1) neighbor lookup."""
    
    def __init__(self):
        self.adjacency: dict[str, list[PropagationEdge]] = {}
        self.reverse_adjacency: dict[str, list[PropagationEdge]] = {}
        self.node_index: dict[str, set[str]] = {}
    
    def add_edge(self, edge: PropagationEdge):
        """Add edge with O(1) complexity."""
        self.adjacency.setdefault(edge.source_id, []).append(edge)
        self.reverse_adjacency.setdefault(edge.target_id, []).append(edge)
        self.node_index.setdefault(edge.source_id, set()).add(edge.target_id)
```

**Batch Processing:**
```python
def process_events_batch(events: list[Event]) -> list[EventContract]:
    """Process events in batch for efficiency."""
    contracts = []
    
    # Group by related tickers for shared graph building
    ticker_groups = _group_by_tickers(events)
    
    for ticker, group_events in ticker_groups.items():
        # Build shared graph for same-ticker events
        shared_graph = _build_shared_graph(ticker, group_events)
        
        for event in group_events:
            contract = _extract_contract(event, shared_graph)
            contracts.append(contract)
    
    return contracts
```

### 6.4 Storage Optimization

**Incremental Graph Updates:**
```python
def update_graph_incrementally(
    graph: PropagationGraph,
    new_event: Event,
    theses: list[Thesis],
    positions: list[Position],
) -> PropagationGraph:
    """Add new event to existing graph without full rebuild."""
    # Only process new edges
    new_edges = _compute_new_edges(new_event, theses, positions, graph)
    
    # Validate no cycles introduced
    if _would_create_cycle(graph, new_edges):
        raise ValueError("New edges would create cycle")
    
    # Add edges incrementally
    for edge in new_edges:
        graph.add_edge(edge)
    
    # Revalidate topological order
    graph.topological_sort()
    
    return graph
```

---

## 7. Error Handling and Recovery Patterns

### 7.1 Error Classification

```python
class EventError(SynapseError):
    """Base class for event-related errors."""
    code = "EVENT_ERROR"

class EventDetectionError(EventError):
    """Detection failed."""
    code = "EVENT_DETECTION_FAILED"

class PropagationCycleError(EventError):
    """Cycle detected in propagation graph."""
    code = "PROPAGATION_CYCLE_DETECTED"

class PropagationStuckError(EventError):
    """Event stuck in propagating state."""
    code = "PROPAGATION_STUCK"

class ContractBuildError(EventError):
    """EventContract build failed."""
    code = "CONTRACT_BUILD_FAILED"
```

### 7.2 Recovery Strategies

```python
class EventRecoveryManager:
    """Handle event processing failures."""
    
    def recover_detection_failure(
        self,
        event: Event,
        error: EventDetectionError,
    ) -> Event:
        """Recover from detection failure by using fallback defaults."""
        # Set confidence to low
        event.confidence = 0.1
        event.source = "manual"
        return event
    
    def recover_propagation_cycle(
        self,
        graph: PropagationGraph,
        cycle: list[str],
    ) -> PropagationGraph:
        """Recover from cycle by removing weakest edge."""
        # Find edge with lowest weight in cycle
        weakest_edge = self._find_weakest_edge_in_cycle(graph, cycle)
        
        # Remove edge
        graph.edges = [e for e in graph.edges if e != weakest_edge]
        
        # Revalidate
        graph.topological_sort()
        
        return graph
    
    def recover_stuck_propagation(
        self,
        contract: EventContract,
    ) -> EventContract:
        """Recover stuck propagation by forcing settlement."""
        contract.propagation_state = PropagationState.EXPIRED
        contract.expired_at = datetime.now(CST)
        return contract
```

### 7.3 Idempotency

```python
def process_event_idempotent(
    event: Event,
    existing_contracts: list[EventContract],
) -> EventContract:
    """Process event idempotently — safe to retry."""
    # Check if already processed
    existing = next(
        (c for c in existing_contracts if c.event_id == event.id),
        None,
    )
    
    if existing:
        # Already processed, return existing
        return existing
    
    # Process new event
    contract = process_event(event)
    return contract
```

### 7.4 Activity Logging

```python
class ActivityType(str, Enum):
    # Existing...
    EVENT_DETECTED = "event.detected"
    EVENT_PROPAGATED = "event.propagated"
    EVENT_SETTLED = "event.settled"
    EVENT_EXPIRED = "event.expired"
    EVENT_CONTRACT_BUILT = "event.contract_built"
```

---

## 8. Configuration Model

### 8.1 Event Type Registry

```yaml
# configs/event_types.yaml
event_types:
  earnings:
    display_name: "财报公告"
    default_decay_rate: 0.15
    default_confidence: 0.8
    stuck_timeout_days: 7
    detectors:
      - name: "earnings_announcement_detector"
        enabled: true
        rules:
          - field: "event_type"
            operator: "equals"
            value: "earnings"
  
  policy:
    display_name: "政策事件"
    default_decay_rate: 0.05
    default_confidence: 0.9
    stuck_timeout_days: 14
    detectors:
      - name: "policy_change_detector"
        enabled: true
  
  sentiment:
    display_name: "市场情绪"
    default_decay_rate: 0.3
    default_confidence: 0.5
    stuck_timeout_days: 3
    detectors:
      - name: "sentiment_detector"
        enabled: true
  
  theme:
    display_name: "主题投资"
    default_decay_rate: 0.1
    default_confidence: 0.7
    stuck_timeout_days: 10
    detectors:
      - name: "theme_detector"
        enabled: true
  
  capital_flow:
    display_name: "资金流向"
    default_decay_rate: 0.2
    default_confidence: 0.6
    stuck_timeout_days: 5
    detectors:
      - name: "capital_flow_detector"
        enabled: true
```

### 8.2 Propagation Configuration

```yaml
# configs/propagation.yaml
propagation:
  # Graph limits
  max_nodes_per_graph: 100
  max_edges_per_graph: 200
  max_propagation_depth: 5
  max_concurrent_propagations: 10
  
  # Cycle detection
  cycle_detection_enabled: true
  cycle_resolution_strategy: "remove_weakest_edge"
  
  # Decay configuration
  decay_calculation: "exponential"  # "linear" | "exponential"
  decay_threshold: 0.1
  
  # Stuck protection
  default_stuck_timeout_days: 7
  stuck_force_expire: true
```

### 8.3 Detector Configuration

```yaml
# configs/detectors.yaml
detectors:
  registry:
    module: "synapse.event.detection"
    class: "DetectorRegistry"
  
  detectors:
    - name: "earnings_announcement"
      event_type: "earnings"
      module: "synapse.event.detection.earnings"
      class: "EarningsDetector"
      enabled: true
      confidence_threshold: 0.7
    
    - name: "policy_change"
      event_type: "policy"
      module: "synapse.event.detection.policy"
      class: "PolicyDetector"
      enabled: true
      confidence_threshold: 0.8
    
    - name: "sentiment"
      event_type: "sentiment"
      module: "synapse.event.detection.sentiment"
      class: "SentimentDetector"
      enabled: false  # P4 scope
      confidence_threshold: 0.5
    
    - name: "theme"
      event_type: "theme"
      module: "synapse.event.detection.theme"
      class: "ThemeDetector"
      enabled: true
      confidence_threshold: 0.6
    
    - name: "capital_flow"
      event_type: "capital_flow"
      module: "synapse.event.detection.capital_flow"
      class: "CapitalFlowDetector"
      enabled: true
      confidence_threshold: 0.6
```

---

## 9. Component Structure

### 9.1 Module Layout

```
synapse/
  event/
    __init__.py
    schemas/
      __init__.py
      event.py              # Event v3.0
      event_contract.py     # EventContract
      propagation_edge.py   # PropagationEdge
      propagation_graph.py  # PropagationGraph
    
    detection/
      __init__.py
      registry.py           # DetectorRegistry
      base.py               # EventDetector ABC
      earnings.py           # EarningsDetector
      policy.py             # PolicyDetector
      sentiment.py          # SentimentDetector (P4)
      theme.py              # ThemeDetector
      capital_flow.py       # CapitalFlowDetector
      deduplication.py      # Event deduplication
    
    propagation/
      __init__.py
      graph_builder.py      # Graph construction
      cycle_detector.py     # Tarjan's algorithm
      topological_sort.py   # Kahn's algorithm
      decay_calculator.py   # Decay computation
      state_machine.py      # Event lifecycle
    
    analysis/
      __init__.py
      impact_analyzer.py    # EventImpactAnalyzer
      correlation.py        # EventReviewCorrelation
      drift_integration.py  # DriftDetector integration
      bias_integration.py   # BiasDetector integration
    
    workflow/
      __init__.py
      detection_flow.py     # Event detection workflow
      propagation_flow.py   # Event propagation workflow
      settlement_flow.py    # Event settlement workflow
    
    cli/
      __init__.py
      event_commands.py     # synapse event ...
```

### 9.2 CLI Commands

```python
# synapse event detect
def detect_events(data_dir: str, config_path: str) -> list[Event]:
    """Detect events from data directory."""
    pass

# synapse event impact
def show_event_impact(event_id: str, workspace: str) -> ImpactReport:
    """Show impact analysis for an event."""
    pass

# synapse event graph
def show_propagation_graph(entity_id: str, workspace: str) -> PropagationGraph:
    """Show propagation graph for an entity."""
    pass

# synapse event list
def list_events(
    state: Optional[str] = None,
    event_type: Optional[str] = None,
    workspace: str = ".",
) -> list[Event]:
    """List events with optional filters."""
    pass
```

---

## 10. Data Flow Summary

```
+-----------------+     +-----------------+     +-----------------+
|   Data Input    | --> |   Detection     | --> |   Deduplication |
| (YAML/JSON)     |     |   Engine        |     |   & Merge       |
+-----------------+     +-----------------+     +-----------------+
                                                          |
                                                          v
+-----------------+     +-----------------+     +-----------------+
|   Settlement    | <-- |   Propagation   | <-- |   Graph         |
|   Flow          |     |   State Machine |     |   Builder       |
+-----------------+     +-----------------+     +-----------------+
        |
        v
+-----------------+     +-----------------+     +-----------------+
|   Impact        | --> |   Analytics     | --> |   Activity      |
|   Analysis      |     |   Integration   |     |   Logging       |
+-----------------+     +-----------------+     +-----------------+
```

---

## 11. Key Recommendations

1. **Start with Event v3.0 extension** — Build on proven Lazy Upcast pattern, maintain backward compatibility
2. **Implement graph builder first** — Core DAG logic is foundation for all other components
3. **Add stuck timeout from day one** — Prevent infinite propagation states
4. **Use Tarjan's for cycle detection** — Proven algorithm, O(V+E) complexity
5. **Configuration-driven detectors** — Allow adding new event types without code changes

---

## 12. Risk Mitigation

| Risk | Mitigation | Priority |
|------|-----------|----------|
| Schema migration | Lazy Upcast pattern | HIGH |
| Graph performance | DAG constraints + batch processing | MEDIUM |
| Cycle detection | Tarjan's algorithm + stuck timeout | HIGH |
| Scope creep | Strict Non-Goals enforcement | HIGH |
| Integration with P2 | Existing projection model extends cleanly | LOW |

---

## 13. Next Steps

1. Create `synapse/event/` module structure
2. Implement Event v3.0 schema with backward compatibility
3. Build PropagationGraph with cycle detection
4. Implement EventStateMachine
5. Create pluggable detector pattern
6. Add EventContract builder
7. Integrate with existing analytics layer
8. Add CLI commands
9. Write comprehensive tests

---

*Analysis completed: 2026-05-18*
*Component scope: #8-#13 (Event Schema Registry, Detection Engine, Propagation Graph, Impact Analyzer, Review Integration, CLI)*
