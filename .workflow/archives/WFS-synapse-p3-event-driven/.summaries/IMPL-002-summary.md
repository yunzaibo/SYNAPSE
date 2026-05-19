# Task: IMPL-002 DetectorRegistry + BaseDetector Interface + Event Taxonomy

## Implementation Summary

### Files Created/Modified

- `synapse/event/base.py` (create): BaseDetector ABC with 3 abstract methods
- `synapse/event/registry.py` (create): DetectorRegistry for registration/lookup of detectors
- `synapse/event/taxonomy.py` (create): Event taxonomy constants for 6 A-share event types
- `synapse/event/__init__.py` (modify): Added lazy imports for base, registry, taxonomy exports alongside existing graph imports
- `tests/unit/test_event_detection.py` (create): 14 tests across 3 test classes

### Content Added

**BaseDetector** (`synapse/event/base.py`):
- `BaseDetector(ABC)` -- abstract base class for pluggable event detectors
- `detect(data: dict) -> Optional[Event]` -- analyze data, return Event if detected
- `event_type() -> str` -- return the event type string this detector handles
- `confidence_score(data: dict) -> float` -- return confidence in [0.0, 1.0]

**DetectorRegistry** (`synapse/event/registry.py`):
- `DetectorRegistry` class with internal `dict[str, type[BaseDetector]]` storage
- `register(detector_cls)` -- register detector by calling event_type() on dummy instance; validates BaseDetector subclass
- `get_detector(event_type) -> Optional[type[BaseDetector]]` -- lookup by event type
- `list_detectors() -> dict[str, type[BaseDetector]]` -- return shallow copy of all registered detectors
- `unregister(event_type) -> Optional[type[BaseDetector]]` -- remove and return detector
- `detect_all(data) -> list[Event]` -- run all detectors against data, collect matching events

**Event Taxonomy** (`synapse/event/taxonomy.py`):
- `EVENT_TYPES: dict[str, str]` -- 6 A-share event types with descriptions (earnings, policy, sentiment, theme, capital_flow, corporate_action)
- `SOURCE_PRIORITY: dict[str, int]` -- source-to-priority mapping for deduplication (cninfo=0 highest, manual=3 lowest)
- `EVENT_CATEGORY_MAP: dict[str, list[str]]` -- groups event types by category (financial, regulatory, market_data, thematic)
- `PRIORITY_LEVELS: dict[str, str]` -- propagation priority P0-P3 with descriptions

## Outputs for Dependent Tasks

### Available Components

```python
from synapse.event.base import BaseDetector
from synapse.event.registry import DetectorRegistry
from synapse.event.taxonomy import EVENT_TYPES, SOURCE_PRIORITY, EVENT_CATEGORY_MAP, PRIORITY_LEVELS

# Or via lazy imports:
from synapse.event import BaseDetector, DetectorRegistry, EVENT_TYPES
```

### Integration Points

- **BaseDetector**: Subclass this to implement concrete detectors (e.g., EarningsDetector for IMPL-003)
- **DetectorRegistry**: Instantiate and call `register()` to add detectors, `detect_all()` for bulk detection
- **EVENT_TYPES**: Use keys as event_type strings matching `EventType` enum values in `synapse.core.schemas.event`
- **SOURCE_PRIORITY**: Use for deduplication -- lower number = higher authority (cninfo > aggregators > manual)

### Usage Examples

```python
from synapse.event.registry import DetectorRegistry
from synapse.event.base import BaseDetector
from synapse.core.schemas.event import Event, EventType

class EarningsDetector(BaseDetector):
    def detect(self, data):
        if data.get("has_earnings"):
            return Event(id="...", event_type=EventType.EARNINGS, title="Q1 report")
        return None

    def event_type(self):
        return "earnings"

    def confidence_score(self, data):
        return 0.9

registry = DetectorRegistry()
registry.register(EarningsDetector)
events = registry.detect_all({"has_earnings": True})
```

## Status: Complete
