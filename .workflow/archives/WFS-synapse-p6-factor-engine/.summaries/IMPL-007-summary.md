# Task: IMPL-007 Event Factor Integration

## Implementation Summary

### Files Modified
- `synapse/factor/factors/__init__.py`: Added imports and exports for EventFactor, SentimentFactor, CapitalFlowFactor, PolicyFactor, enrich_with_events
- `synapse/factor/__init__.py`: Added top-level exports for event factor classes and enrich_with_events

### Files Created
- `synapse/factor/factors/event_factor.py`: Event-derived factor implementations (F-016)
- `tests/unit/test_event_factors.py`: 43 tests covering all event factor functionality

### Content Added

- **EventFactor** (`synapse/factor/factors/event_factor.py`): Abstract base class for event-derived factors, inherits from BaseFactor
- **SentimentFactor** (`synapse/factor/factors/event_factor.py`): Engagement-weighted average social media sentiment score (factor_id: `sentiment_score`)
- **CapitalFlowFactor** (`synapse/factor/factors/event_factor.py`): Institutional vs retail capital flow signal (factor_id: `capital_flow_signal`)
- **PolicyFactor** (`synapse/factor/factors/event_factor.py`): Composite policy impact score = severity * confidence * impact_weight (factor_id: `policy_impact`)
- **enrich_with_events()** (`synapse/factor/factors/event_factor.py`): Bridge function that injects event-derived columns (social_sentiment_count, capital_flow_mean, policy_mean_severity, etc.) into a DataFrame by grouping events by related_tickers
- **_IMPACT_WEIGHTS** (`synapse/factor/factors/event_factor.py`): Mapping of ImpactLevel enum values to numeric weights (low=0.25, medium=0.5, high=1.0, unknown=0.5)

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.factor.factors.event_factor import (
    EventFactor,
    SentimentFactor,
    CapitalFlowFactor,
    PolicyFactor,
    enrich_with_events,
)

# Or via top-level
from synapse.factor import (
    EventFactor,
    SentimentFactor,
    CapitalFlowFactor,
    PolicyFactor,
    enrich_with_events,
)
```

### Integration Points
- **SentimentFactor**: Requires DataFrame with `sentiment_score` and `engagement_count` columns (matches SocialMediaSignal schema fields)
- **CapitalFlowFactor**: Requires DataFrame with `institutional_flow` and `retail_flow` columns
- **PolicyFactor**: Requires DataFrame with `severity`, `confidence`, and `impact_level` columns (matches Event schema fields)
- **enrich_with_events()**: Takes `pd.DataFrame` (must have `ticker` column) + `list[Event]`, returns enriched DataFrame with 7 event aggregate columns
- **FactorRegistry**: All 3 event factors register under category `"event"`, filterable via `registry.list_by_category("event")`

### Usage Examples
```python
# Compute sentiment factor from social media signals
import pandas as pd
from synapse.factor import SentimentFactor

signals_df = pd.DataFrame({
    "sentiment_score": [0.8, -0.3, 0.5],
    "engagement_count": [100, 50, 200],
})
factor = SentimentFactor()
scores = factor.compute(signals_df)

# Enrich stock DataFrame with event signals
from synapse.factor import enrich_with_events
from synapse.core.schemas.event import Event, EventType

stock_df = pd.DataFrame({"ticker": ["600519.SH", "000001.SZ"], "close": [1800, 15]})
events = [Event(id="e1", event_type=EventType.POLICY, title="Rate cut", related_tickers=["600519.SH"], severity=0.8)]
enriched = enrich_with_events(stock_df, events)

# Register all event factors in registry
from synapse.factor import FactorRegistry, SentimentFactor, CapitalFlowFactor, PolicyFactor
registry = FactorRegistry()
for cls in [SentimentFactor, CapitalFlowFactor, PolicyFactor]:
    registry.register(cls)
event_factors = registry.list_by_category("event")  # 3 factors
```

## Status: Complete
