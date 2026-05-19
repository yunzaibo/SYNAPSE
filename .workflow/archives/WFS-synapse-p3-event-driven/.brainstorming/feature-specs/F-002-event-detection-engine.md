# F-002: Event Detection Engine

## Component #9: Pluggable Event Detectors

### Overview
Rule-based event detection engine with pluggable detector pattern. Each event type has a dedicated detector that fires when conditions are met. Supports event deduplication and merge logic.

### Architecture

```
DetectorRegistry
├── EarningsDetector
├── PolicyDetector
├── SentimentDetector
├── ThemeDetector
├── CapitalFlowDetector
└── CorporateActionDetector
```

### Detector Interface
```python
class BaseDetector(ABC):
    @abstractmethod
    def detect(self, data: dict) -> Optional[Event]:
        """Return Event if detected, None otherwise."""

    @abstractmethod
    def event_type(self) -> str:
        """Return event type string."""

    @abstractmethod
    def confidence_score(self, data: dict) -> float:
        """Return confidence 0.0-1.0."""
```

### Event Taxonomy (A-Share Specific)
| Category | Sub-Types | Data Sources |
|----------|-----------|--------------|
| earnings | Q1-Q4 reports, pre-announcement, revision, audit opinion | cninfo, AKShare |
| policy | CSRC rules, PBOC rate/RRR, fiscal policy, trading rules | csrc.gov.cn, pboc.gov.cn |
| corporate_action | 增发/配股/分红/股权激励/股东变动/并购重组/回购 | cninfo |
| sentiment | 融资融券, 北向资金, 大宗交易, 龙虎榜 | HKEX, exchange data |
| theme | 政策主题, 行业轮动, 概念板块 | news, manual |
| capital_flow | 主力资金, 散户资金, ETF申赎 | AKShare, Wind |

### Deduplication Rules
- Hash-based dedup key: sha256(event_type + entity_id + date + source)
- Source priority: cninfo > aggregators > manual
- Merge strategy: take highest confidence, combine descriptions
- Conflict resolution: latest source wins for factual data

### Tests (~15 tests)
- Detector fires correctly for each event type
- Detector returns None for non-matching data
- Confidence scoring per event type
- Deduplication: same event from multiple sources
- Deduplication: different events with similar data
- Event merge logic
- DetectorRegistry registration and lookup
