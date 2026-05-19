# Task: IMPL-001 Event Schema v3.0 + EventContract + PropagationEdge

## Implementation Summary

### Files Modified
- `synapse/core/schemas/event.py`: Extended Event with 7 v3.0 fields, added 2 enums, added 4 A-share event types
- `synapse/core/schemas/__init__.py`: Added EventContract, PropagationEdge, EventSourceType, PropagationState exports
- `tests/unit/test_schemas.py`: Updated schema_version assertion from "2.0" to "3.0" for Event v3.0 default

### Files Created
- `synapse/core/schemas/event_contract.py`: EventContract schema (11 fields, to_dict/from_dict)
- `synapse/core/schemas/propagation_edge.py`: PropagationEdge schema (11 fields, to_dict/from_dict, weight validation)
- `tests/unit/test_event_schemas.py`: 12 tests across 5 test classes

### Content Added

#### Event Schema v3.0 (`synapse/core/schemas/event.py`)
- **EventSourceType enum**: `data_feed`, `news`, `manual`, `ai_detected`
- **PropagationState enum**: `detected`, `propagating`, `settled`, `expired`
- **EventType extended**: +`SENTIMENT`, `THEME`, `CAPITAL_FLOW`, `CORPORATE_ACTION`
- **Event dataclass new fields**:
  - `severity: float = 0.5` (0.0-1.0, validated)
  - `confidence: float = 0.5` (0.0-1.0, validated)
  - `decay_rate: float = 0.1`
  - `source: EventSourceType = EventSourceType.MANUAL`
  - `propagation_state: PropagationState = PropagationState.DETECTED`
  - `propagation_graph_id: Optional[str] = None`
  - `contract_id: Optional[str] = None`
- **Lazy Upcast**: `from_dict()` uses `data.get()` with defaults for all 7 new fields

#### EventContract Schema (`synapse/core/schemas/event_contract.py`)
- **EventContract dataclass** (inherits BaseSchema):
  - `contract_id`, `event_id`: identity
  - `affected_theses`, `affected_positions`: entity references
  - `impact_scores: dict[str, float]`: entity_id -> impact score
  - `aggregate_impact: float`, `propagation_depth: int`
  - `settled_at: Optional[datetime]`

#### PropagationEdge Schema (`synapse/core/schemas/propagation_edge.py`)
- **PropagationEdge dataclass** (inherits BaseSchema):
  - `edge_id`, `source_id`, `src_entity_type` ("event"|"thesis")
  - `target_id`, `tgt_entity_type` ("thesis"|"position")
  - `weight: float` (0.0-1.0, validated), `decay_rate: float`, `edge_type: str`
  - Note: `src_entity_type`/`tgt_entity_type` renamed from `source_type`/`target_type` to avoid shadowing BaseSchema.source_type

### Test Results
```
12 passed in 0.16s (test_event_schemas.py)
29 passed in 0.22s (test_schemas.py -- existing, no regressions)
41 total passed
```

### Key Design Decisions
- **Field naming**: `src_entity_type`/`tgt_entity_type` instead of `source_type`/`target_type` to avoid collision with BaseSchema.source_type (SourceType enum)
- **created_at**: Not overridden in new schemas -- uses BaseSchema's datetime field
- **settled_at**: Uses Optional[datetime] for proper serialization
- **Constraint validation**: `__post_init__` raises ValueError for out-of-range severity/confidence/weight

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.core.schemas.event import Event, EventType, ImpactLevel, EventSourceType, PropagationState
from synapse.core.schemas.event_contract import EventContract
from synapse.core.schemas.propagation_edge import PropagationEdge
```

### Integration Points
- **Event v3.0**: All 7 new fields have Lazy Upcast defaults -- v2.0 consumers unaffected
- **EventContract**: Links events to theses/positions with impact_scores dict
- **PropagationEdge**: Directed graph edges with weight/decay for propagation modeling

## Status: Complete
