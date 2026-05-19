# P3 Event-Driven Research Contracts — Guidance Specification

## 1. Executive Summary

P3 extends SYNAPSE's research memory layer with event-driven research contracts. While P0-P2 built the core research loop and analytics, P3 adds the ability to detect, track, and propagate market events that influence research decisions.

## 2. Concepts & Terminology

| Term | Definition | Aliases | Category |
|------|-----------|---------|----------|
| Event Contract | A structured record of a market event with lifecycle, impact scope, and propagation state | Research Contract | Core |
| Event Type | Classification of market events (announcement, policy, sentiment, theme, capital flow) | — | Taxonomy |
| Event Propagation | The mechanism by which an event's influence spreads across related theses/positions | Cascade, Spread | Behavior |
| Event Decay | Temporal reduction of event impact over time | Fade, Attrition | Temporal |
| Event Confidence | Reliability score of event detection (0.0–1.0) | Certainty | Quality |
| Propagation Graph | Directed graph of event → thesis/position influence paths | Impact Graph | Structure |
| Event Source | Origin of event detection (data feed, news, manual) | — | Origin |

## 3. Non-Goals (Explicitly Excluded)

- **Real-time trading execution** — P3 is research-only, no order routing
- **Automated sentiment NLP** — P4 handles Chinese financial NLP; P3 defines the contract model only
- **External data API integration** — P3 defines schemas; actual feed integration is P4+
- **UI/dashboard** — CLI-only for now; UI is a separate initiative
- **Machine learning models** — P3 uses rule-based detection; ML is future scope

## 4. Component Breakdown (Proposed)

### Component #8: Event Schema Registry
- Extend existing `Event` schema with event type taxonomy
- Add event severity, confidence, decay parameters
- Maintain backward compatibility via Lazy Upcast

### Component #9: Event Detection Engine
- Rule-based event detectors for each event type
- Pluggable detector architecture (new types added via config)
- Event deduplication and merge logic

### Component #10: Event Propagation Graph
- Directed acyclic graph of event → thesis/position influence
- Propagation scoring with decay factors
- Cycle detection and circular reference protection

### Component #11: Event Impact Analyzer
- Quantify event impact on positions and theses
- Before/after comparison metrics
- Risk-adjusted impact scores

### Component #12: Event-Review Integration
- Link events to review outcomes (which reviews were event-driven)
- Event-informed decision tracking
- Post-event thesis revision detection

### Component #13: Event CLI Subcommands
- `synapse event detect --data-dir PATH`
- `synapse event impact --event-id ID`
- `synapse event graph --position-id ID`

### Component #14: Sentiment Viral Propagation (F-007)
- Model sentiment propagation as graph with viral coefficient (R₀)
- BFS-based cascade detection within configurable time window (default 24h)
- Decay uses CATEGORY_HALF_LIVES["sentiment"] = 2.0 days
- Integration: edge_type="sentiment" on PropagationGraph, settlement via EventContract

### Component #15: Capital Flow Divergence Tracking (F-008)
- Track institutional vs retail flow divergence with normalized score
- Divergence classification: bullish (>0.3), bearish (<-0.3), neutral
- 5-day rolling window for flow comparison
- Integration: divergence events create EventContract with settlement_result

### Component #16: Cross-Event Correlation Engine (F-009)
- Correlate events affecting overlapping theses within time window (default 7d)
- EVENT_TYPE_AFFINITY matrix for type-based scoring
- Combined impact: amplification (same direction) vs dampening (different direction)
- Integration: correlation edges added to PropagationGraph (bidirectional)

## 5. Data Model Direction

### Event Schema v3.0 Extension (Lazy Upcast)
```python
# New fields on existing Event schema
event_type: str          # "announcement" | "policy" | "sentiment" | "theme" | "capital_flow"
severity: float         # 0.0–1.0
confidence: float       # 0.0–1.0
decay_rate: float       # per-day decay factor
source: str             # "data_feed" | "news" | "manual" | "ai_detected"
propagation_state: str  # "detected" | "propagating" | "settled" | "expired"
```

### New: EventContract (standalone schema)
```python
@dataclass
class EventContract:
    contract_id: str
    event_id: str                     # links to Event
    affected_theses: list[str]        # thesis IDs
    affected_positions: list[str]     # position IDs
    impact_scores: dict[str, float]   # thesis_id → impact
    propagation_path: list[str]       # chain of affected entities
    created_at: str
    settled_at: Optional[str]
```

### New: PropagationEdge (graph edge)
```python
@dataclass
class PropagationEdge:
    source_id: str      # event or thesis
    target_id: str      # thesis or position
    weight: float       # 0.0–1.0
    decay: float        # per-day
    created_at: str
```

## 6. Integration Points with P0-P2

| Existing Component | Integration | Direction |
|-------------------|-------------|-----------|
| Event schema (P1) | Extend with v3 fields | Schema evolves |
| Review schema (P1) | Add event_id reference | Link reviews to events |
| Decision schema (P1) | Add event_trigger field | Track event-driven decisions |
| Thesis schema (P1) | Add event_influence field | Track which events shaped thesis |
| CorrelationAnalyzer (P2) | Feed events with outcome_tracking | Correlation input |
| DriftDetector (P2) | Detect event-induced drift | Drift signal source |
| BiasDetector (P2) | Detect event-reaction bias | Bias input |
| CLI framework (P2) | Add event subcommand group | CLI extension |

## 7. RFC 2119 Constraints

- Event contracts MUST maintain backward compatibility with existing Event schema
- Propagation graph MUST detect and prevent circular references
- Event decay MUST be configurable per event type
- All event detections MUST include confidence scores
- Event propagation MUST be deterministic (same inputs → same graph)
- Event contracts MUST be rebuildable from raw events (projection model)
- F-007: System MUST calculate R₀ for every sentiment event reaching PROPAGATING state
- F-007: System SHOULD flag R₀ > 2.0 as "high-virality" for priority review
- F-008: System MUST compute divergence score for every CapitalFlowDetector event
- F-008: System MUST classify divergence using threshold 0.3
- F-009: System MUST detect correlations within configurable window (default 7 days)
- F-009: System SHOULD flag correlation_score > 0.7 as "high-correlation"
- F-009: System MUST NOT create cycles in correlation graph (DAG property enforced)

## 8. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema migration complexity | High | Lazy Upcast pattern (proven in P2) |
| Propagation graph performance | Medium | DAG constraints + cycle detection |
| Event deduplication accuracy | Medium | Configurable merge rules per type |
| Integration with P2 analytics | Low | Existing projection model extends cleanly |
| Scope creep (NLP, ML) | High | Strict Non-Goals enforcement |

## 9. Recommended Role Selection

For P3 analysis, these roles provide the best coverage:
1. **system-architect** — Propagation graph architecture, event lifecycle
2. **data-architect** — Event schema design, graph data model
3. **subject-matter-expert** — Event types, market event taxonomy, China A-share specifics
4. **test-strategist** — Test strategy for event detection, propagation, integration
