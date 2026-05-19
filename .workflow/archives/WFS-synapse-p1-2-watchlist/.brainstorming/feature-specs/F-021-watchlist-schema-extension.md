# Feature Spec: F-021 - WatchlistEntry Schema Extension

**Priority**: High
**Contributing Roles**: system-architect, data-architect, product-manager
**Status**: Final (conflicts resolved)

## 1. Requirements Summary

- WatchlistEntry dataclass MUST be extended with `priority_score` (float) and `reason` (str) fields
- `priority_score` MUST be validated in `__post_init__` to the range [0.0, 1.0]
- `reason` MUST contain a human-readable explanation of the scoring rationale
- Schema version MUST be bumped from "1.0" to "2.0"
- Existing v1.0 WatchlistEntry dicts MUST deserialize without error via Lazy Upcast pattern
- The `why_now` field MUST NOT be repurposed for scoring reason — it serves a distinct purpose (event description)
- WatchlistEntry.SignalType enum MUST remain independent from `schemas/signal.py.SignalType`
- Frozen dataclass MUST NOT be applied in P1-2 — immutability refactoring is deferred to a separate task
- `to_dict()` MUST serialize `priority_score` rounded to 4 decimal places to avoid floating-point noise
- `from_dict()` MUST NOT raise on missing `priority_score` or `reason` keys

## 2. Design Decisions [CORE SECTION]

### D-021-1: Lazy Upcast for New Fields

**Decision**: The schema MUST use the Lazy Upcast pattern for `priority_score` and `reason`, consistent with the Event v2.0 -> v3.0 transition in `event.py`.

**Context**: Existing YAML files and code produce WatchlistEntry dicts without `priority_score` or `reason`. Adding required fields would break all existing consumers.

**Options Considered**:
- [system-architect] Lazy Upcast with defaults (priority_score=0.0, reason="")
- [data-architect] Lazy Upcast with defaults — same approach
- [product-manager] Default priority_score=0.0 ensures unscored entries naturally sort to the bottom

**Chosen Approach**: Lazy Upcast with `data.get("priority_score", 0.0)` and `data.get("reason", "")` in `from_dict()`. The default `priority_score=0.0` means unscored entries sort to the bottom of any ranking. The default `reason=""` indicates an unscored entry.

**Trade-offs**: Zero migration cost and full backward compatibility vs. no type safety for missing fields at deserialization time. The trade-off is acceptable because the scoring pipeline (F-022) is the only writer of these fields.

**Source**: system-architect, data-architect (consensus)

### D-021-2: Schema Version Bump to "2.0"

**Decision**: `WatchlistEntry.schema_version` MUST be set to "2.0" to distinguish scored entries from unscored ones.

**Context**: Consumers need to detect whether an entry has been through the scoring pipeline. Version "2.0" enables this detection and supports future schema evolution.

**Options Considered**:
- [system-architect] Bump to "2.0" with a sentinel `priority_score > 0` as a secondary check
- [data-architect] Bump to "2.0" — aligns with BaseSchema pattern

**Chosen Approach**: Set `schema_version = "2.0"` as class default. Existing `from_dict()` in BaseSchema handles version strings without issue.

**Trade-offs**: Clear versioning signal vs. minor consumer update needed if consumers branch on version. The impact is low because existing consumers use `from_dict()` which handles unknown fields gracefully.

**Source**: system-architect, data-architect (consensus)

### D-021-3: Frozen Dataclass NOT Applied in P1-2

**Decision**: `@dataclass(frozen=True)` MUST NOT be added to WatchlistEntry in P1-2. This is deferred to a separate refactoring task.

**Context**: The guidance-specification mentions "Frozen Dataclass pattern" but existing code does not use `@dataclass(frozen=True)` on WatchlistEntry. Adding it would break `_build_event_entries()`, `_build_signal_entries()`, and `_build_portfolio_entries()` which create entries imperatively.

**Options Considered**:
- [system-architect] Do NOT add frozen=True in P1-2
- [data-architect] Frozen Dataclass consistency — apply now
- [product-manager] No opinion on implementation detail

**Chosen Approach**: Keep WatchlistEntry as a mutable dataclass. Defer immutability to a separate P2+ refactoring task that also updates all construction sites. (EP-006)

**Trade-offs**: Maintains backward compatibility with existing code vs. delayed immutability guarantee. The trade-off is acceptable because P1-2 focuses on scoring functionality, not data model purity.

**Source**: system-architect (recommended by cross-role analysis)

### D-021-4: priority_score Range and Type

**Decision**: `priority_score` MUST be `float` type, validated to [0.0, 1.0] in `__post_init__`, defaulting to `0.0`.

**Context**: Consistent with `Event.severity` and `Event.confidence` validation patterns. The float type is chosen over Decimal for consistency with existing codebase patterns.

**Options Considered**:
- [system-architect] float with [0.0, 1.0] range, validated in __post_init__
- [data-architect] float with [0.0, 1.0] range, __post_init__ range check

**Chosen Approach**: `float` type, `__post_init__` validation using the existing `_validate_range` pattern from Event. Out-of-range values (e.g., -0.1, 1.1) MUST raise `ValueError`.

**Trade-offs**: Runtime validation catches bugs early vs. slight performance overhead on construction. The overhead is negligible for the expected volume (50-200 entries per day).

**Source**: system-architect, data-architect (consensus)

### D-021-5: reason Field Semantics

**Decision**: The `reason` field MUST contain a human-readable explanation of why the entry received its priority score. It MUST be a plain string — no markdown, no structured data.

**Context**: The existing `why_now` field explains why an entry is relevant today (event description). The new `reason` field explains the scoring rationale (which signals contributed and why the score was assigned).

**Options Considered**:
- [product-manager] reason string length between 10 and 200 characters in generated entries
- [system-architect] reason format: "{top_dimension}: {brief_explanation} (score: {total_score:.2f})"
- [data-architect] reason is plain string, no range constraint at schema level

**Chosen Approach**: reason is a plain string at the schema level. The 10-200 character length is a generation recommendation (enforced by the scoring engine in F-022), not a schema-level constraint. (EP-007)

**Trade-offs**: Flexibility in reason generation vs. no automated length validation at schema level. The trade-off is acceptable because the scoring engine is the only writer and will enforce the recommended range.

**Source**: product-manager (length recommendation), system-architect (format pattern), data-architect (schema-level simplicity)

## 3. Interface Contract

### Data Model Changes

```python
# New fields added to WatchlistEntry
priority_score: float = 0.0   # [0.0, 1.0], validated in __post_init__
reason: str = ""              # Human-readable scoring explanation
```

### Serialization Contract

**to_dict() additions**:
```python
"priority_score": round(self.priority_score, 4),
"reason": self.reason,
```

**from_dict() additions (Lazy Upcast)**:
```python
priority_score=float(data.get("priority_score", 0.0)),
reason=data.get("reason", ""),
```

### Schema Version

```python
schema_version: str = "2.0"  # Bumped from "1.0"
```

### Backward Compatibility

- v1.0 dict -> v2.0 object: defaults applied (priority_score=0.0, reason="")
- v2.0 object -> dict -> v2.0 object: fields preserved exactly
- v2.0 object -> dict -> YAML -> dict -> v2.0 object: full serialization round-trip

## 4. Constraints & Risks

[REVIEW-FLAG] F-021 schema does not define `trigger_type` or `linked_event_id` fields, but F-024 requires `trigger_type == PORTFOLIO_REVIEW` and F-023/F-024 reference `entry.linked_event_id`. These fields must be either (a) added to F-021 schema, (b) confirmed as existing fields from a prior version, or (c) defined in a separate schema extension. This is a cross-feature consistency gap that blocks F-023 and F-024 implementation.

| Constraint | Type | Mitigation |
|------------|------|------------|
| Backward compatibility | MUST | Lazy Upcast with defaults in from_dict() |
| priority_score range [0.0, 1.0] | MUST | __post_init__ validation with ValueError |
| why_now vs reason distinction | MUST NOT | Document distinct semantics; do not repurpose why_now |
| SignalType enum independence | MUST NOT | WatchlistEntry.SignalType stays separate from signal.py.SignalType |
| YAML/JSON round-trip fidelity | MUST | to_dict/from_dict MUST produce identical output for new fields |
| Frozen dataclass NOT applied | MUST NOT | Defer to separate refactoring task (EP-006) |

| Risk | Severity | Mitigation |
|------|----------|------------|
| Existing YAML files lack new fields | LOW | Lazy Upcast with defaults handles this |
| why_now vs reason confusion | MEDIUM | Document distinct semantics clearly in code comments |
| Schema version bump breaks consumers | LOW | Existing consumers use from_dict() which handles unknown fields |

## 5. Acceptance Criteria

- [ ] WatchlistEntry has `priority_score` (float, default 0.0) and `reason` (str, default "") fields
- [ ] `__post_init__` validates priority_score in [0.0, 1.0], raises ValueError for out-of-range
- [ ] `schema_version` defaults to "2.0"
- [ ] `to_dict()` serializes priority_score rounded to 4 decimal places
- [ ] `from_dict()` applies defaults for missing priority_score and reason keys
- [ ] v1.0 dict (no priority_score/reason) deserializes to valid v2.0 entry with defaults
- [ ] v2.0 object -> dict -> v2.0 object round-trip preserves all fields exactly
- [ ] v2.0 object -> dict -> YAML -> dict -> v2.0 object full round-trip works
- [ ] Existing code that creates WatchlistEntry without priority_score/reason continues to work
- [ ] Why_now field is NOT repurposed — distinct from reason field

## 6. Detailed Analysis References

- @../system-architect/analysis-F-021-watchlist-schema-extension.md — Lazy Upcast pattern, schema version bump, frozen dataclass deferral
- @../data-architect/analysis-F-021-watchlist-schema-extension.md — Field definitions, serialization contract, round-trip test requirements
- @../product-manager/analysis-F-021-watchlist-schema-extension.md — User stories, backward compatibility contract, success metrics
- @../guidance-specification.md#feature-decomposition — F-021 definition and related roles

## 7. Cross-Feature Dependencies

- **Depends on**: Existing BaseSchema (synapse/core/schemas/base.py), existing WatchlistEntry definition (synapse/core/schemas/watchlist.py)
- **Required by**: F-022 (scoring engine writes priority_score and reason), F-026 (ranking reads priority_score), F-028 (tests validate schema)
- **Shared patterns**: Lazy Upcast pattern (ADR-005), __post_init__ validation pattern (Event.severity, Event.confidence)
- **Integration points**: F-022 populates priority_score and reason; F-026 reads priority_score for sorting; F-028 validates round-trip serialization
