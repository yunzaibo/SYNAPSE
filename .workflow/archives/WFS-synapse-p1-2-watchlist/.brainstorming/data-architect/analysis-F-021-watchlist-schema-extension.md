# F-021: WatchlistEntry Schema Extension — Data Architect Analysis

## Feature Summary

Extend `WatchlistEntry` with two new fields: `priority_score` (float, 0.0-1.0) and `reason` (str). Apply Lazy Upcast pattern for backward compatibility with existing v1.0 WatchlistEntry dicts.

## Data Model Changes

### Current WatchlistEntry Fields (v1.0)

```
BaseSchema: id, schema_version, status, created_at, updated_at, source_type, created_by, market_context
Own fields: ticker, symbol, market, headline, why_now, signals, research_angle, action, risk_hint, trigger_type, linked_thesis_id, linked_event_id
```

### New Fields (v2.0)

| Field | Type | Default | Range | Validation |
|-------|------|---------|-------|------------|
| `priority_score` | `float` | `0.0` | [0.0, 1.0] | `__post_init__` range check |
| `reason` | `str` | `""` | non-empty after scoring | No range constraint |

### Schema Version Bump

`schema_version` class default MUST change from `"1.0"` to `"2.0"` in the WatchlistEntry class definition. The `BaseSchema.schema_version` default remains `"1.0"` — each subclass overrides as needed.

## Serialization Contract

### to_dict Additions

```python
"priority_score": round(self.priority_score, 4),
"reason": self.reason,
```

`priority_score` SHOULD be rounded to 4 decimal places in serialization to avoid floating-point noise in YAML output.

### from_dict Additions (Lazy Upcast)

```python
priority_score=float(data.get("priority_score", 0.0)),
reason=data.get("reason", ""),
```

**MUST NOT raise** on missing `priority_score` or `reason` — old v1.0 dicts will not have these fields. Default `0.0` and `""` ensure the object is valid.

### Round-Trip Test Requirements

1. v2.0 object → dict → v2.0 object: fields preserved exactly
2. v1.0 dict (no priority_score/reason) → v2.0 object: defaults applied
3. v2.0 object → dict → YAML → dict → v2.0 object: full serialization round-trip
4. priority_score boundary values: 0.0, 1.0, 0.5 all serialize/deserialize correctly
5. priority_score out-of-range (e.g., -0.1, 1.1) MUST raise ValueError in `__post_init__`

## Constraints

- `priority_score` MUST be validated in `__post_init__` with range [0.0, 1.0], consistent with `Event.severity` and `Event.confidence` validation pattern
- `reason` MUST be a plain string — no markdown, no structured data. It is a human-readable explanation of why this entry is on the watchlist
- The existing `why_now` field serves a different purpose (event description) and MUST NOT be repurposed for scoring reason
- `WatchlistEntry.SignalType` enum MUST remain independent from `schemas/signal.py.SignalType` per D-008

## Risks

- **Low**: Existing YAML files without `priority_score` will parse correctly due to Lazy Upcast defaults
- **Medium**: If downstream consumers assume `priority_score > 0` means "scored", they must handle the `0.0` default for unscored entries. Recommendation: treat `0.0` as "not yet scored" sentinel.
