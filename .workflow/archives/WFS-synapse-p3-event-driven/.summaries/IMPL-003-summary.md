# Task: IMPL-003 Concrete Detectors + Event Deduplication

## Implementation Summary

### Files Created
- `synapse/event/detectors.py` — 6 concrete detector classes implementing BaseDetector
- `synapse/event/dedup.py` — DeduplicationEngine with SHA-256 hash-based dedup keys

### Files Modified
- `synapse/event/__init__.py` — Added lazy imports for 6 detectors + DeduplicationEngine
- `tests/unit/test_event_detection.py` — Added 9 new tests (TestConcreteDetectors + TestDeduplication)

### Content Added

**EarningsDetector** (`synapse/event/detectors.py:33`):
- Fires on `report_type` in {Q1-Q4}, `eps_surprise` > 0, or `pre_announcement` = True
- Confidence: 0.5 (report) + 0.3 (surprise) + 0.2 (pre-announcement), capped at 1.0

**PolicyDetector** (`synapse/event/detectors.py:76`):
- Fires on `source` in {csrc.gov.cn, pboc.gov.cn} or `policy_type` in {rate_cut, rate_hike, rrr_cut, rrr_hike, fiscal_stimulus, csrc_rule}
- Confidence: 0.95 for official sources, 0.7 for valid policy types

**SentimentDetector** (`synapse/event/detectors.py:117`):
- Fires on `margin_change_pct`, `northbound_flow`, `block_trade_count`, or `dragon_tiger_count`
- Confidence: 0.4 + 0.15 per signal, capped at 1.0

**ThemeDetector** (`synapse/event/detectors.py:158`):
- Fires on `policy_theme`, `sector_rotation`, or `concept_sector` (non-empty strings)
- Confidence: 0.5 + 0.15 per theme, capped at 1.0

**CapitalFlowDetector** (`synapse/event/detectors.py:196`):
- Fires on `mainforce_flow`, `retail_flow`, or `etf_net_inflow` (non-zero)
- Confidence: 0.4 + 0.2 per flow, capped at 1.0

**CorporateActionDetector** (`synapse/event/detectors.py:233`):
- Fires on `action_type` in {secondary_offering, rights_issue, dividend, equity_incentive, shareholder_change, ma_restructuring, buyback}
- Confidence: 0.85 for valid action types

**DeduplicationEngine** (`synapse/event/dedup.py:16`):
- `compute_dedup_key(event_type, entity_id, date_str, source)` — SHA-256 hash
- `merge_events(event_a, event_b)` — Highest confidence wins, descriptions combined with " | "
- `resolve_conflicts(events)` — Groups by dedup key, merges within groups

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.event.detectors import (
    EarningsDetector, PolicyDetector, SentimentDetector,
    ThemeDetector, CapitalFlowDetector, CorporateActionDetector,
)
from synapse.event.dedup import DeduplicationEngine

# Or via lazy imports:
from synapse.event import EarningsDetector, DeduplicationEngine
```

### Integration Points
- All 6 detectors register in DetectorRegistry via `registry.register(EarningsDetector)`
- `DetectorRegistry.detect_all(data)` runs all registered detectors
- `DeduplicationEngine.resolve_conflicts(events)` deduplicates event lists using SOURCE_PRIORITY

### Usage Examples
```python
from synapse.event.registry import DetectorRegistry
from synapse.event.detectors import EarningsDetector, PolicyDetector
from synapse.event.dedup import DeduplicationEngine

# Register detectors
registry = DetectorRegistry()
registry.register(EarningsDetector)
registry.register(PolicyDetector)

# Detect events from data
events = registry.detect_all({"report_type": "Q3", "eps_surprise": 0.5})

# Deduplicate events from multiple sources
engine = DeduplicationEngine()
unique_events = engine.resolve_conflicts(events)
```

## Status: Complete
