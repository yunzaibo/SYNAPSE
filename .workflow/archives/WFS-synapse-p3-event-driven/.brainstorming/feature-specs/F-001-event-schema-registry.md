# F-001: Event Schema Registry

## Component #8: Event Schema v3.0 + EventContract + PropagationEdge

### Overview
Extend the existing Event schema with event type taxonomy, severity, confidence, decay, and propagation state. Introduce two new schemas: EventContract (links events to theses/positions) and PropagationEdge (directed graph edges).

### Data Model

#### Event Schema v3.0 (Lazy Upcast from v2.0)
```python
@dataclass
class Event(Base):
    # Existing v2.0 fields (unchanged)
    event_id: str
    title: str
    description: str
    date: str
    category: str
    outcome_tracking: list[OutcomeRecord]
    linked_review_ids: list[str]
    calibration_score: float

    # New v3.0 fields
    event_type: str          # "earnings" | "policy" | "sentiment" | "theme" | "capital_flow" | "corporate_action"
    severity: float          # 0.0-1.0 (normalized from 1-5 scale)
    confidence: float        # 0.0-1.0
    decay_rate: float        # per-day decay factor (default 0.1)
    source: str              # "data_feed" | "news" | "manual" | "ai_detected"
    propagation_state: str   # "detected" | "propagating" | "settled" | "expired"
    propagation_graph_id: Optional[str]
    contract_id: Optional[str]

    schema_version: float = 3.0
```

#### EventContract (new schema)
```python
@dataclass
class EventContract(Base):
    contract_id: str
    event_id: str
    affected_theses: list[str]
    affected_positions: list[str]
    impact_scores: dict[str, float]    # entity_id → impact score
    aggregate_impact: float
    propagation_depth: int
    created_at: str
    settled_at: Optional[str]
    schema_version: float = 1.0
```

#### PropagationEdge (new schema)
```python
@dataclass
class PropagationEdge(Base):
    edge_id: str
    source_id: str           # event or thesis ID
    source_type: str         # "event" | "thesis"
    target_id: str           # thesis or position ID
    target_type: str         # "thesis" | "position"
    weight: float            # 0.0-1.0
    decay_rate: float        # per-day
    edge_type: str           # "influence" | "trigger" | "correlation"
    created_at: str
    schema_version: float = 1.0
```

### Storage Strategy
- Hybrid: adjacency list in EventContract + edge list as independent YAML files
- Consistent with P0-P2 file-per-entity pattern
- In-memory graph built at query time

### Backward Compatibility
- v2.0 consumers ignore new fields via `data.get()` defaults
- All writes produce v3.0
- No migration scripts needed (Lazy Upcast)

### Tests (~12 tests)
- Schema round-trip for Event v3.0
- Schema round-trip for EventContract
- Schema round-trip for PropagationEdge
- Lazy Upcast v2.0 → v3.0 compatibility
- Constraint validation (severity, confidence, weight ranges)
