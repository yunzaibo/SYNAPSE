# F-044: Financial Sentiment Lexicon

**Feature ID**: F-044
**Priority**: Medium
**Related Roles**: subject-matter-expert, data-architect

## Objective

Build and maintain a domain-specific sentiment dictionary with 500+ Chinese financial terms.

## Scope

- Sentiment term categorization (bullish/bearish/neutral)
- Domain-specific term scoring (financial context)
- Negation and degree modifier handling
- Lexicon update mechanism

## Lexicon Structure

### Term Categories

| Category | Example Terms | Count | Sentiment |
|----------|--------------|-------|-----------|
| Growth | 高增长, 超预期, 扭亏为盈, 景气度提升 | 80+ | bullish |
| Decline | 业绩下滑, 亏损扩大, 景气度下降, 扣非亏损 | 70+ | bearish |
| Risk | 高风险, 商誉减值, 质押风险, 诉讼风险 | 60+ | bearish |
| Opportunity | 低估, 安全边际, 成长空间, 行业龙头 | 50+ | bullish |
| Market | 涨停, 跌停, 北向资金流入, 融资余额增加 | 60+ | context |
| Regulatory | 政策利好, 监管收紧, IPO放缓, 降准降息 | 50+ | context |
| Neutral | 公告, 披露, 召开, 审议 | 100+ | neutral |

### Term Entry Format

```json
{
  "term": "扭亏为盈",
  "sentiment": "bullish",
  "score": 0.8,
  "category": "growth",
  "context_window": 5,
  "negation_sensitive": true
}
```

## Technical Requirements

- MUST contain 500+ domain-specific financial sentiment terms
- MUST support negation detection (不看好, 未达预期)
- MUST support degree modifiers (非常, 极其, 略微)
- MUST be loadable as external YAML/JSON file
- MUST extend existing LexiconAnalyzer (synapse/event/social.py)
- SHOULD support term frequency weighting
- SHOULD allow user customization (add/remove terms)

## Integration Points

- LexiconAnalyzer (synapse/event/social.py) — enhance
- NewsSentimentDetector (F-039) — primary consumer
- ResearchReportDetector (F-038) — secondary consumer

## Acceptance Criteria

1. 500+ terms across 7 categories
2. Negation handling correctly flips sentiment for 90%+ of cases
3. Lexicon loads in <100ms
4. Custom terms can be added via YAML without code changes
