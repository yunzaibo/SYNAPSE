# Feature Spec: F-028 - Watchlist Tests

**Priority**: High
**Contributing Roles**: system-architect, data-architect, product-manager
**Status**: Final (conflicts resolved)

## 1. Requirements Summary

- Test suite MUST extend existing test_projection.py with comprehensive tests for scoring, ranking, filtering, and serialization
- Test coverage MUST be >= 80% for scoring, ranking, and filtering code
- Golden file regression tests MUST exist for the scoring engine
- Tests MUST be deterministic: no random data, no time-dependent assertions
- Tests MUST be independent: no shared mutable state between tests
- Test data MUST be defined as pytest fixtures, not inline
- Mock data MUST cover edge cases: empty signals, missing positions, non-trading-day events
- Tests MUST run with `py -m pytest -p no:asyncio` (Windows requirement)
- Round-trip serialization tests MUST validate v1.0 -> v2.0 upcast and v2.0 -> dict -> v2.0 fidelity
- Scoring determinism tests MUST verify identical inputs produce identical outputs

## 2. Design Decisions [CORE SECTION]

### D-028-1: Test File Structure

**Decision**: Tests MUST be organized into separate files by feature, following the existing test_projection.py pattern.

**Context**: The system-architect proposes separate test files per feature. The data-architect proposes test categories within a single file. The product-manager requires >= 80% coverage.

**Options Considered**:
- [system-architect] Separate files: test_watchlist_schema.py, test_scoring_engine.py, etc.
- [data-architect] Test categories within organized pytest classes
- [product-manager] >= 80% coverage target

**Chosen Approach**: Separate test files per feature for clarity and maintainability. Each file focuses on one feature's behavior. Integration tests verify cross-feature behavior.

```
tests/
  test_watchlist_schema.py      # F-021: Schema extension tests
  test_scoring_engine.py        # F-022: Core scoring tests
  test_event_decay_scoring.py   # F-023: Event decay integration
  test_portfolio_scoring.py     # F-024: Portfolio-aware scoring
  test_market_validation.py     # F-025: Market semantics tests
  test_ranking_filtering.py     # F-026: Ranking and filtering
  test_scoring_config.py        # F-027: Configuration tests
  test_watchlist_integration.py # Cross-feature integration
```

**Trade-offs**: Clear separation vs. more files to manage. The separation is preferred because each file can be run independently and has a clear scope.

**Source**: system-architect (file structure), product-manager (coverage target)

### D-028-2: Test Isolation and Fixtures

**Decision**: Each test MUST be independent. Test data MUST be defined as pytest fixtures producing fresh objects.

**Context**: The system-architect and data-architect agree on test isolation. Fixtures produce fresh objects for each test, aligned with the frozen dataclass pattern.

**Options Considered**:
- [system-architect] Independent tests, fixture-based data
- [data-architect] Test independence, factory functions for fixtures

**Chosen Approach**: pytest fixtures with factory functions. Each fixture produces fresh objects. No shared mutable state between tests.

```python
@pytest.fixture
def default_config() -> ScoringConfig:
    return ScoringConfig()

@pytest.fixture
def sample_events() -> list[Event]:
    return [
        Event(id="evt_1", event_type=EventType.EARNINGS, title="Q1 Earnings",
              event_date=date(2026, 5, 19), severity=0.8, confidence=0.9),
        Event(id="evt_2", event_type=EventType.POLICY, title="Rate Decision",
              event_date=date(2026, 5, 15), severity=0.6, confidence=0.7),
    ]
```

**Trade-offs**: Test reliability vs. slightly more setup code. The trade-off is strongly favorable because isolated tests are easier to debug and parallelize.

**Source**: system-architect, data-architect (consensus)

### D-028-3: Golden File Regression Tests

**Decision**: Golden file tests MUST exist for the scoring engine with known inputs and expected outputs.

**Context**: The product-manager requires golden file tests to catch scoring drift. These tests serve dual purpose: regression detection and living documentation.

**Options Considered**:
- [product-manager] Golden file tests with known inputs/expected outputs
- [system-architect] Determinism testing: same inputs produce same outputs

**Chosen Approach**: Golden file tests with fixed input data and expected priority_score values (within 0.01 tolerance). The golden files document expected behavior and catch any scoring algorithm changes.

**Trade-offs**: Living documentation vs. maintenance burden when scoring algorithm changes. The trade-off is favorable because golden files catch unintended regressions.

**Source**: product-manager (golden files), system-architect (determinism)

### D-028-4: Edge Case Coverage

**Decision**: Tests MUST cover edge cases: empty inputs, single entry, multiple entries with same ticker, all entries below min_score, config with extreme weights, schema version mismatch.

**Context**: The system-architect and data-architect define comprehensive edge case lists. The product-manager requires mock data covering edge cases.

**Options Considered**:
- [system-architect] Empty inputs, single entry, dedup, all filtered, extreme config
- [data-architect] Edge cases for each test category

**Chosen Approach**: Comprehensive edge case coverage as defined by both system-architect and data-architect. Each test category has specific edge cases.

| Category | Edge Cases |
|----------|-----------|
| Schema | v1.0 upcast, boundary values (0.0, 1.0), out-of-range |
| Scoring | Empty inputs, single dimension, all dimensions, weight sum != 1.0 |
| Decay | Fresh event, aged event, expired, no date, future date, zero rate |
| Portfolio | Active/WEAKENED/INVALIDATED thesis, RISING/FADING/STABLE attention, non-positioned |
| Ranking | Descending order, tie-breaking, min score, max entries, empty input |
| Config | Missing file, malformed YAML, extreme weights, custom weights |

**Trade-offs**: Comprehensive coverage vs. test maintenance burden. The trade-off is favorable because edge cases are where bugs hide.

**Source**: system-architect, data-architect, product-manager (consensus)

### D-028-5: Determinism Testing

**Decision**: Scoring engine tests MUST verify determinism: same inputs produce identical outputs.

**Context**: The system-architect emphasizes determinism as critical for ADR-009 daily regeneration. The product-manager requires deterministic scoring.

**Options Considered**:
- [system-architect] Determinism testing: run scoring twice, compare outputs
- [product-manager] Golden file tests catch scoring drift

**Chosen Approach**: Explicit determinism test: run scoring engine twice with identical inputs, assert outputs are identical. Additionally, golden file tests provide regression-level determinism verification.

**Trade-offs**: Explicit verification vs. implicit through golden files. Both approaches are used for defense in depth.

**Source**: system-architect (determinism), product-manager (golden files)

## 3. Interface Contract

### Test Categories and Targets

| Category | Scope | Priority | Count Target | Coverage Target |
|----------|-------|----------|-------------|----------------|
| Schema Round-Trip | F-021 | HIGH | 6 | 100% to_dict/from_dict |
| Scoring Engine | F-022 | HIGH | 8 | 100% branch coverage |
| Event Decay | F-023 | HIGH | 6 | 100% branch coverage |
| Portfolio Scoring | F-024 | HIGH | 6 | 100% branch coverage |
| Market Validation | F-025 | MEDIUM | 4 | 80% path coverage |
| Ranking/Filtering | F-026 | HIGH | 8 | 100% path coverage |
| Config Loading | F-027 | MEDIUM | 5 | 80% branch coverage |
| Integration | Cross | HIGH | 3 | End-to-end pipeline |

### Key Test Cases

**F-021: Schema Round-Trip**
- `test_watchlist_entry_v2_round_trip` — v2.0 object -> dict -> v2.0 object
- `test_watchlist_entry_v1_upcast` — v1.0 dict -> v2.0 object with defaults
- `test_watchlist_entry_yaml_round_trip` — full YAML serialization round-trip
- `test_priority_score_validation` — out-of-range raises ValueError
- `test_priority_score_boundary` — 0.0 and 1.0 preserved
- `test_reason_preserved` — special characters preserved

**F-022: Scoring Engine**
- `test_scoring_deterministic` — same inputs produce same scores
- `test_scoring_with_no_data` — empty inputs produce zero scores
- `test_scoring_aggregation_weights` — weights respected
- `test_scoring_auto_normalize` — weights sum != 1.0 auto-normalized
- `test_scoring_graceful_degradation` — missing data handled gracefully
- `test_scored_entry_frozen` — ScoredEntry is immutable
- `test_scoring_result_frozen` — ScoringResult is immutable
- `test_reason_format` — reason follows structured format

**F-026: Ranking**
- `test_ranking_descending_order` — sorted by priority_score descending
- `test_tie_breaking_by_ticker` — same score sorted by ticker
- `test_dedup_highest_score` — duplicate tickers keep highest
- `test_min_score_filter` — entries below threshold removed
- `test_max_entries_limit` — top-N truncation
- `test_at_least_one_guarantee` — at least 1 entry if any exist
- `test_filtered_count_accuracy` — count matches actual removals
- `test_empty_input` — empty input produces empty RankedWatchlist

### Test Execution

```bash
# Windows requirement per MEMORY.md
py -m pytest -p no:asyncio tests/test_watchlist_*.py -v
```

## 4. Constraints & Risks

| Constraint | Type | Mitigation |
|------------|------|------------|
| Test coverage >= 80% | MUST | Coverage tool integrated into CI |
| Golden file tests catch scoring drift | MUST | Any scoring change must update golden files |
| Tests are deterministic | MUST | No random data, fixed timestamps |
| Tests are independent | MUST | No shared mutable state |
| Mock data covers edge cases | SHOULD | Factory functions for fixtures |
| Tests run on Windows | MUST | py -m pytest -p no:asyncio |

| Risk | Severity | Mitigation |
|------|----------|------------|
| Test file may grow large | LOW | Organize into pytest classes by feature |
| Fixtures may become stale | LOW | Use factory functions, not hardcoded dicts |
| Flaky tests from date dependency | MEDIUM | Mock date.today() in tests |
| Slow test execution | LOW | Tests are pure Python, no I/O |

## 5. Acceptance Criteria

- [ ] Test files exist for each feature (F-021 through F-028)
- [ ] Schema round-trip tests: v2.0, v1.0 upcast, YAML round-trip, boundary values
- [ ] Scoring engine tests: determinism, empty inputs, weight normalization, graceful degradation
- [ ] Decay tests: fresh, aged, expired, no date, future date, zero rate
- [ ] Portfolio tests: thesis status, attention state, non-positioned ticker
- [ ] Ranking tests: descending order, tie-breaking, dedup, min score, max entries, at-least-one
- [ ] Config tests: defaults, validation, custom weights, missing file
- [ ] Integration test: end-to-end pipeline from mock inputs to final watchlist
- [ ] All tests are independent (no shared mutable state)
- [ ] Test data defined as pytest fixtures with factory functions
- [ ] Coverage >= 80% for scoring, ranking, and filtering code
- [ ] Golden file tests exist with known inputs and expected outputs
- [ ] Tests run with `py -m pytest -p no:asyncio`

## 6. Detailed Analysis References

- @../system-architect/analysis-F-028-watchlist-tests.md — Test architecture, key test cases, determinism testing, edge cases
- @../data-architect/analysis-F-028-watchlist-tests.md — Test categories, fixtures, coverage targets
- @../product-manager/analysis-F-028-watchlist-tests.md — User stories, golden files, success metrics
- @../guidance-specification.md#feature-decomposition — F-028 definition and related roles

## 7. Cross-Feature Dependencies

- **Depends on**: F-021 (schema), F-022 (scoring engine), F-023 (event filtering), F-024 (portfolio scoring), F-025 (market validation), F-026 (ranking/filtering), F-027 (config)
- **Required by**: All features rely on tests for quality assurance
- **Shared patterns**: pytest fixtures, factory functions, deterministic testing
- **Integration points**:
  - Each feature's tests validate its specific behavior
  - Integration test verifies cross-feature behavior (schema + scoring + ranking)
  - Existing `test_projection.py`: Follow same patterns and conventions
  - CI/CD: Tests MUST pass before `git push` per CLAUDE.md rules
