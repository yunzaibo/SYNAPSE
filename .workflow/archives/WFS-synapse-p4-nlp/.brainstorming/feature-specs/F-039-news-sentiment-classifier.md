# F-039: News Sentiment Classifier

**Feature ID**: F-039
**Priority**: High
**Related Roles**: system-architect, data-architect, subject-matter-expert

## Objective

Classify Chinese financial news sentiment as bullish/bearish/neutral with aspect-level granularity.

## Scope

- Domain-specific sentiment classification (financial vs general)
- Aspect-level sentiment for multi-aspect texts
- Confidence scoring
- Integration with existing LexiconAnalyzer

## Data Model

**Input**: TextDocument (news article text)
**Output**: SentimentResult (frozen dataclass) containing:
- label: bullish/bearish/neutral
- confidence: float [0.0, 1.0]
- aspect_sentiments: tuple[AspectSentiment, ...] (optional)
  - aspect: str (e.g., "earnings", "management", "market")
  - label: bullish/bearish/neutral
  - confidence: float

## Technical Requirements

- MUST achieve >85% accuracy on financial news classification
- MUST use domain-specific sentiment lexicon (500+ terms)
- MUST handle negation and degree modifiers (不看好, 非常乐观)
- MUST implement BaseDetector for P3 integration
- SHOULD augment lexicon-based analysis with transformer model
- SHOULD cache lexicon in memory for fast access

## Domain Requirements

- Financial sentiment differs from general: 高增长=bullish, 高风险=bearish
- Must handle financial abbreviations (营收, 净利, 扣非)
- Must understand market-specific expressions (涨停, 跌停, 北向资金流入)

## Integration Points

- LexiconAnalyzer (synapse/event/social.py) — enhance with 500+ terms
- Sentiment propagation (P3 F-007)
- EventBuilder → SOCIAL_SENTIMENT event type

## Acceptance Criteria

1. >85% accuracy on labeled financial news dataset
2. Processes 100 articles/minute on CPU
3. Handles mixed sentiment (e.g., "业绩增长但估值偏高")
