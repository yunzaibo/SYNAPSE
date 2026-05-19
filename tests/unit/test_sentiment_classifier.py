"""Unit tests for sentiment classifier -- F-039 News Sentiment Classifier.

Tests cover: bullish/bearish/neutral classification, aspect sentiment,
negation handling, degree modifiers, frozen dataclass, edge cases,
and serialization round-trips. 18 test methods.
"""

import pytest

from synapse.nlp.aspect_detector import AspectDetector, AspectResult
from synapse.nlp.sentiment_classifier import (
    AspectSentiment,
    BULLISH_THRESHOLD,
    BEARISH_THRESHOLD,
    NewsSentimentClassifier,
    SentimentResult,
)


# ---------------------------------------------------------------------------
# SentimentResult frozen dataclass
# ---------------------------------------------------------------------------

class TestSentimentResult:
    """Tests for SentimentResult frozen dataclass."""

    def test_default_values(self) -> None:
        result = SentimentResult()
        assert result.label == "neutral"
        assert result.confidence == 0.0
        assert result.score == 0.0
        assert result.aspect_sentiments == ()
        assert result.processing_time_ms == 0.0

    def test_frozen(self) -> None:
        result = SentimentResult(label="bullish", confidence=0.8)
        with pytest.raises(AttributeError):
            result.label = "bearish"  # type: ignore[misc]

    def test_to_dict(self) -> None:
        result = SentimentResult(
            label="bullish",
            confidence=0.8,
            score=0.5,
            aspect_sentiments=(
                AspectSentiment(aspect="earnings", label="bullish", confidence=0.9),
            ),
            processing_time_ms=1.5,
        )
        d = result.to_dict()
        assert d["label"] == "bullish"
        assert d["confidence"] == 0.8
        assert d["score"] == 0.5
        assert len(d["aspect_sentiments"]) == 1
        assert d["aspect_sentiments"][0]["aspect"] == "earnings"
        assert d["processing_time_ms"] == 1.5

    def test_from_dict_roundtrip(self) -> None:
        original = SentimentResult(
            label="bearish",
            confidence=0.6,
            score=-0.4,
            aspect_sentiments=(
                AspectSentiment(aspect="risk", label="bearish", confidence=0.7),
                AspectSentiment(aspect="market", label="neutral", confidence=0.1),
            ),
            processing_time_ms=2.3,
        )
        d = original.to_dict()
        restored = SentimentResult.from_dict(d)
        assert restored.label == original.label
        assert restored.confidence == original.confidence
        assert restored.score == original.score
        assert len(restored.aspect_sentiments) == 2
        assert restored.processing_time_ms == original.processing_time_ms


# ---------------------------------------------------------------------------
# AspectSentiment frozen dataclass
# ---------------------------------------------------------------------------

class TestAspectSentiment:
    """Tests for AspectSentiment frozen dataclass."""

    def test_default_values(self) -> None:
        asp = AspectSentiment()
        assert asp.aspect == ""
        assert asp.label == "neutral"
        assert asp.confidence == 0.0

    def test_frozen(self) -> None:
        asp = AspectSentiment(aspect="earnings", label="bullish", confidence=0.9)
        with pytest.raises(AttributeError):
            asp.label = "bearish"  # type: ignore[misc]

    def test_to_dict_from_dict_roundtrip(self) -> None:
        original = AspectSentiment(aspect="market", label="bullish", confidence=0.75)
        d = original.to_dict()
        restored = AspectSentiment.from_dict(d)
        assert restored.aspect == "market"
        assert restored.label == "bullish"
        assert restored.confidence == 0.75


# ---------------------------------------------------------------------------
# AspectDetector
# ---------------------------------------------------------------------------

class TestAspectDetector:
    """Tests for AspectDetector keyword-based aspect identification."""

    def setup_method(self) -> None:
        self.detector = AspectDetector()

    def test_earnings_detection(self) -> None:
        results = self.detector.detect("业绩大幅增长超预期")
        aspects = [r.aspect for r in results]
        assert "earnings" in aspects

    def test_market_detection(self) -> None:
        results = self.detector.detect("股价涨停，北向资金流入")
        aspects = [r.aspect for r in results]
        assert "market" in aspects

    def test_risk_detection(self) -> None:
        results = self.detector.detect("公司面临诉讼风险")
        aspects = [r.aspect for r in results]
        assert "risk" in aspects

    def test_multiple_aspects(self) -> None:
        results = self.detector.detect("业绩增长但估值偏高，监管趋严")
        aspects = set(r.aspect for r in results)
        assert "earnings" in aspects
        assert "market" in aspects
        assert "regulatory" in aspects

    def test_no_aspect(self) -> None:
        results = self.detector.detect("今天天气不错")
        assert len(results) == 0

    def test_empty_text(self) -> None:
        results = self.detector.detect("")
        assert len(results) == 0

    def test_detect_aspects_returns_tuples(self) -> None:
        pairs = self.detector.detect_aspects("业绩增长")
        assert isinstance(pairs, list)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in pairs)

    def test_detect_single_unique_aspects(self) -> None:
        aspects = self.detector.detect_single("业绩增长，业绩超预期")
        assert aspects == ["earnings"]

    def test_supported_aspects(self) -> None:
        supported = self.detector.supported_aspects()
        assert "earnings" in supported
        assert "management" in supported
        assert "market" in supported
        assert "regulatory" in supported
        assert "risk" in supported
        assert len(supported) >= 5


# ---------------------------------------------------------------------------
# NewsSentimentClassifier -- classification
# ---------------------------------------------------------------------------

class TestNewsSentimentClassifier:
    """Tests for NewsSentimentClassifier sentiment classification."""

    def setup_method(self) -> None:
        self.classifier = NewsSentimentClassifier()

    def test_bullish_text(self) -> None:
        result = self.classifier.classify("业绩大幅增长超预期，净利润增长")
        assert result.label == "bullish"
        assert result.score > 0
        assert result.confidence > 0

    def test_bearish_text(self) -> None:
        result = self.classifier.classify("亏损扩大，业绩下滑")
        assert result.label == "bearish"
        assert result.score < 0
        assert result.confidence > 0

    def test_neutral_text(self) -> None:
        result = self.classifier.classify("公司召开股东大会")
        assert result.label == "neutral"
        assert result.confidence >= 0

    def test_empty_text(self) -> None:
        result = self.classifier.classify("")
        assert result.label == "neutral"
        assert result.confidence == 0.0
        assert result.score == 0.0

    def test_score_range(self) -> None:
        result = self.classifier.classify(
            "业绩超预期业绩增长涨停"
        )
        assert -1.0 <= result.score <= 1.0
        assert 0.0 <= result.confidence <= 1.0

    def test_confidence_equals_abs_score(self) -> None:
        result = self.classifier.classify("涨停")
        assert result.confidence == pytest.approx(abs(result.score), abs=1e-6)

    def test_processing_time_non_negative(self) -> None:
        result = self.classifier.classify("test")
        assert result.processing_time_ms >= 0

    def test_batch_classification(self) -> None:
        texts = [
            "业绩大幅增长",
            "亏损扩大",
            "公司召开股东大会",
        ]
        results = self.classifier.classify_batch(texts)
        assert len(results) == 3
        assert results[0].label == "bullish"
        assert results[1].label == "bearish"
        assert results[2].label == "neutral"


# ---------------------------------------------------------------------------
# Negation and degree modifiers
# ---------------------------------------------------------------------------

class TestNegationAndDegree:
    """Tests for negation handling and degree modifier integration."""

    def setup_method(self) -> None:
        self.classifier = NewsSentimentClassifier()

    def test_negation_flips_bullish(self) -> None:
        """Negation should reduce or flip bullish sentiment."""
        result_no_neg = self.classifier.classify("业绩超预期")
        result_neg = self.classifier.classify("业绩不达预期")
        # Negated version should be less bullish or bearish
        assert result_neg.score <= result_no_neg.score

    def test_degree_amplifies_bullish(self) -> None:
        """Strong degree modifier should increase bullish score."""
        result_normal = self.classifier.classify("业绩增长")
        result_strong = self.classifier.classify("业绩大幅增长")
        assert result_strong.score >= result_normal.score


# ---------------------------------------------------------------------------
# Custom thresholds
# ---------------------------------------------------------------------------

class TestCustomThresholds:
    """Tests for custom classification thresholds."""

    def test_custom_bullish_threshold(self) -> None:
        classifier = NewsSentimentClassifier(
            bullish_threshold=0.05, bearish_threshold=-0.05
        )
        # "涨停" scores 0.4 -- should be bullish with default or lower threshold
        result = classifier.classify("涨停")
        assert result.label == "bullish"

    def test_strict_thresholds_neutral(self) -> None:
        classifier = NewsSentimentClassifier(
            bullish_threshold=0.9, bearish_threshold=-0.9
        )
        # "涨停" scores 0.4 -- below strict 0.9 threshold should be neutral
        result = classifier.classify("涨停")
        assert result.label == "neutral"


# ---------------------------------------------------------------------------
# Aspect-level sentiment
# ---------------------------------------------------------------------------

class TestAspectSentimentIntegration:
    """Tests for aspect-level sentiment in classification results."""

    def setup_method(self) -> None:
        self.classifier = NewsSentimentClassifier()

    def test_aspect_sentiments_populated(self) -> None:
        result = self.classifier.classify("业绩大幅增长，股价涨停")
        # At least one aspect should be detected
        assert len(result.aspect_sentiments) >= 1
        aspects = [a.aspect for a in result.aspect_sentiments]
        assert "earnings" in aspects or "market" in aspects

    def test_aspect_sentiment_labels(self) -> None:
        result = self.classifier.classify("业绩大幅增长超预期")
        for asp in result.aspect_sentiments:
            assert asp.label in ("bullish", "bearish", "neutral")
            assert 0.0 <= asp.confidence <= 1.0

    def test_no_aspects_for_plain_text(self) -> None:
        result = self.classifier.classify("hello world")
        assert len(result.aspect_sentiments) == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def setup_method(self) -> None:
        self.classifier = NewsSentimentClassifier()

    def test_mixed_sentiment_text(self) -> None:
        """Mixed sentiment should produce a score reflecting both sides."""
        # "业绩增长超预期" (bullish) + "业绩下滑" (bearish)
        result = self.classifier.classify(
            "业绩增长超预期，但业绩下滑风险加大"
        )
        # Score should be between -1 and 1
        assert -1.0 <= result.score <= 1.0
        # Label should be one of the three
        assert result.label in ("bullish", "bearish", "neutral")

    def test_very_short_text(self) -> None:
        # Single character that is not in lexicon
        result = self.classifier.classify("a")
        assert result.label in ("bullish", "bearish", "neutral")

    def test_very_long_text(self) -> None:
        long_text = "业绩增长超预期。" * 100
        result = self.classifier.classify(long_text)
        assert result.label == "bullish"
        assert result.processing_time_ms >= 0

    def test_special_characters(self) -> None:
        result = self.classifier.classify("test!@#$%^&*()")
        assert result.label in ("bullish", "bearish", "neutral")

    def test_numbers_in_text(self) -> None:
        result = self.classifier.classify("业绩增长超预期，净利润增长50%")
        assert result.label == "bullish"
