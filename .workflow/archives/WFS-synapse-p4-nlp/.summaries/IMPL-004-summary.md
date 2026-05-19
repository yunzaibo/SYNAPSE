# Task: IMPL-004 News Sentiment Classifier

## Implementation Summary

### Files Created
- `synapse/nlp/aspect_detector.py`: Keyword-based financial aspect identification with 5 aspect categories
- `synapse/nlp/sentiment_classifier.py`: NewsSentimentClassifier with SentimentResult/AspectSentiment frozen dataclasses
- `tests/unit/test_sentiment_classifier.py`: 36 unit tests covering classification, aspects, negation, edge cases

### Files Modified
- `synapse/nlp/__init__.py`: Added lazy imports for NewsSentimentClassifier, SentimentResult, AspectSentiment, AspectDetector, AspectResult

### Content Added

**AspectDetector** (`synapse/nlp/aspect_detector.py`):
- `ASPECT_KEYWORDS` dict: 5 aspect categories with 30+ keywords each (earnings, management, market, regulatory, risk)
- `AspectResult` frozen dataclass: aspect, sentence, keyword (3 fields, frozen=True, slots=True)
- `AspectDetector` frozen dataclass: keyword-based aspect identification
  - `detect_aspects(text) -> list[tuple[str, str]]`: returns (aspect, sentence) pairs
  - `detect(text) -> list[AspectResult]`: returns full detail results
  - `detect_single(text) -> list[str]`: returns unique aspect names
  - `supported_aspects() -> list[str]`: returns supported aspect names

**SentimentResult** (`synapse/nlp/sentiment_classifier.py:42`):
- Frozen dataclass with 5 fields: label, confidence, score, aspect_sentiments, processing_time_ms
- `to_dict()` / `from_dict()` round-trip serialization

**AspectSentiment** (`synapse/nlp/sentiment_classifier.py:20`):
- Frozen dataclass with 3 fields: aspect, label, confidence
- `to_dict()` / `from_dict()` round-trip serialization

**NewsSentimentClassifier** (`synapse/nlp/sentiment_classifier.py:100`):
- Pipeline: TextPreprocessor -> EnhancedLexiconAnalyzer -> AspectDetector -> threshold classification
- `classify(text) -> SentimentResult`: single text classification
- `classify_batch(texts) -> list[SentimentResult]`: batch classification
- Configurable thresholds: bullish_threshold (default 0.1), bearish_threshold (default -0.1)
- Threshold logic: score > 0.1 -> bullish, score < -0.1 -> bearish, else neutral
- Confidence = abs(score), clamped to [0.0, 1.0]

**Constants** (`synapse/nlp/sentiment_classifier.py`):
- `BULLISH_THRESHOLD = 0.1`
- `BEARISH_THRESHOLD = -0.1`
- `_VALID_LABELS = frozenset({"bullish", "bearish", "neutral"})`

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.nlp.sentiment_classifier import (
    NewsSentimentClassifier,
    SentimentResult,
    AspectSentiment,
    BULLISH_THRESHOLD,
    BEARISH_THRESHOLD,
)
from synapse.nlp.aspect_detector import (
    AspectDetector,
    AspectResult,
    ASPECT_KEYWORDS,
)
```

### Integration Points
- **NewsSentimentClassifier.classify()**: Input Chinese text, output SentimentResult with label/confidence/score/aspects
- **AspectDetector**: Reusable for any aspect-level analysis beyond sentiment
- **SentimentResult.to_dict()**: Serialize for storage or API responses
- **SentimentPropagation** (synapse/event/sentiment.py): SentimentResult.score can feed into R0/cascade detection

### Usage Examples
```python
# Basic classification
classifier = NewsSentimentClassifier()
result = classifier.classify("业绩大幅增长超预期")
assert result.label == "bullish"
assert result.confidence > 0

# Aspect-level analysis
result = classifier.classify("业绩增长，股价涨停")
for aspect in result.aspect_sentiments:
    print(f"{aspect.aspect}: {aspect.label} ({aspect.confidence:.2f})")

# Batch processing
results = classifier.classify_batch(["text1", "text2", "text3"])

# Custom thresholds
strict = NewsSentimentClassifier(bullish_threshold=0.5, bearish_threshold=-0.5)

# Aspect detection standalone
detector = AspectDetector()
aspects = detector.detect_single("业绩增长，监管趋严")
# -> ["earnings", "regulatory"]
```

## Test Results
- 36 tests collected, 36 passed
- Coverage: bullish/bearish/neutral classification, aspect sentiment, negation handling, degree modifiers, frozen dataclass, edge cases, serialization round-trips

## Status: Complete
