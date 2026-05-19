"""NewsSentimentClassifier -- Chinese financial news sentiment classification.

Classifies news text as bullish/bearish/neutral with aspect-level granularity.
Pipeline: TextPreprocessor -> EnhancedLexiconAnalyzer -> AspectDetector ->
threshold-based label assignment.

Part of P4 Chinese Financial NLP Layer (F-039).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from synapse.nlp.aspect_detector import AspectDetector, AspectResult
from synapse.nlp.lexicon.scorer import EnhancedLexiconAnalyzer
from synapse.nlp.text_preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BULLISH_THRESHOLD: float = 0.1
BEARISH_THRESHOLD: float = -0.1

_LABEL_BULLISH = "bullish"
_LABEL_BEARISH = "bearish"
_LABEL_NEUTRAL = "neutral"

_VALID_LABELS: frozenset[str] = frozenset({
    _LABEL_BULLISH, _LABEL_BEARISH, _LABEL_NEUTRAL,
})


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AspectSentiment:
    """Sentiment result for a single financial aspect.

    Attributes
    ----------
    aspect:
        Financial aspect name (e.g. "earnings", "market").
    label:
        Sentiment label: "bullish", "bearish", or "neutral".
    confidence:
        Confidence score in [0.0, 1.0].
    """

    aspect: str = ""
    label: str = _LABEL_NEUTRAL
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "aspect": self.aspect,
            "label": self.label,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AspectSentiment:
        return cls(
            aspect=data.get("aspect", ""),
            label=data.get("label", _LABEL_NEUTRAL),
            confidence=float(data.get("confidence", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class SentimentResult:
    """Complete sentiment classification result for a document.

    Attributes
    ----------
    label:
        Overall sentiment label: "bullish", "bearish", or "neutral".
    confidence:
        Confidence score in [0.0, 1.0]. Equals abs(score) when using
        threshold-based classification.
    score:
        Raw sentiment score in [-1.0, 1.0] from the lexicon analyzer.
    aspect_sentiments:
        Tuple of per-aspect sentiment results. Empty if no aspects detected.
    processing_time_ms:
        Time taken to classify the document in milliseconds.
    """

    label: str = _LABEL_NEUTRAL
    confidence: float = 0.0
    score: float = 0.0
    aspect_sentiments: tuple[AspectSentiment, ...] = ()
    processing_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "score": self.score,
            "aspect_sentiments": [a.to_dict() for a in self.aspect_sentiments],
            "processing_time_ms": self.processing_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SentimentResult:
        return cls(
            label=data.get("label", _LABEL_NEUTRAL),
            confidence=float(data.get("confidence", 0.0)),
            score=float(data.get("score", 0.0)),
            aspect_sentiments=tuple(
                AspectSentiment.from_dict(a)
                for a in data.get("aspect_sentiments", [])
            ),
            processing_time_ms=float(data.get("processing_time_ms", 0.0)),
        )


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def _assign_label(score: float) -> str:
    """Assign sentiment label based on threshold.

    Parameters
    ----------
    score:
        Sentiment score in [-1.0, 1.0].

    Returns
    -------
    "bullish" if score > 0.1, "bearish" if score < -0.1, else "neutral".
    """
    if score > BULLISH_THRESHOLD:
        return _LABEL_BULLISH
    if score < BEARISH_THRESHOLD:
        return _LABEL_BEARISH
    return _LABEL_NEUTRAL


def _compute_confidence(score: float) -> float:
    """Compute confidence from score magnitude.

    Confidence = abs(score), clamped to [0.0, 1.0].

    Parameters
    ----------
    score:
        Sentiment score in [-1.0, 1.0].

    Returns
    -------
    Confidence in [0.0, 1.0].
    """
    return min(abs(score), 1.0)


@dataclass
class NewsSentimentClassifier:
    """Chinese financial news sentiment classifier.

    Pipeline:
    1. TextPreprocessor -- abbreviation expansion and normalization
    2. EnhancedLexiconAnalyzer -- lexicon-based sentiment scoring
    3. AspectDetector -- identify financial aspects in text
    4. Threshold-based label assignment (score > 0.1 -> bullish, < -0.1 -> bearish)
    5. Confidence = abs(score)

    Usage::

        classifier = NewsSentimentClassifier()
        result = classifier.classify("业绩大幅增长超预期")
        assert result.label == "bullish"

    Attributes
    ----------
    analyzer:
        EnhancedLexiconAnalyzer instance for scoring.
    preprocessor:
        TextPreprocessor for text normalization.
    aspect_detector:
        AspectDetector for financial aspect identification.
    bullish_threshold:
        Score above which text is classified as bullish (default 0.1).
    bearish_threshold:
        Score below which text is classified as bearish (default -0.1).
    """

    analyzer: EnhancedLexiconAnalyzer = field(
        default_factory=EnhancedLexiconAnalyzer
    )
    preprocessor: TextPreprocessor = field(default_factory=TextPreprocessor)
    aspect_detector: AspectDetector = field(default_factory=AspectDetector)
    bullish_threshold: float = BULLISH_THRESHOLD
    bearish_threshold: float = BEARISH_THRESHOLD

    def classify(self, text: str) -> SentimentResult:
        """Classify the sentiment of a Chinese financial news text.

        Parameters
        ----------
        text:
            Chinese financial news text to classify.

        Returns
        -------
        SentimentResult with label, confidence, score, aspect sentiments,
        and processing time.
        """
        start = time.monotonic()

        if not text:
            return SentimentResult(
                label=_LABEL_NEUTRAL,
                confidence=0.0,
                score=0.0,
                aspect_sentiments=(),
                processing_time_ms=0.0,
            )

        # Step 1: Preprocess
        preprocessed = self.preprocessor.preprocess(text)
        processed_text = preprocessed.expanded

        # Step 2: Score with enhanced lexicon analyzer
        score = self.analyzer.score(processed_text)

        # Step 3: Detect aspects and compute per-aspect scores
        aspect_sentiments = self._compute_aspect_sentiments(processed_text)

        # Step 4: Assign label
        label = self._assign_label(score)

        # Step 5: Compute confidence
        confidence = _compute_confidence(score)

        elapsed_ms = (time.monotonic() - start) * 1000

        return SentimentResult(
            label=label,
            confidence=confidence,
            score=score,
            aspect_sentiments=tuple(aspect_sentiments),
            processing_time_ms=round(elapsed_ms, 2),
        )

    def classify_batch(self, texts: list[str]) -> list[SentimentResult]:
        """Classify multiple texts.

        Parameters
        ----------
        texts:
            List of Chinese financial news texts.

        Returns
        -------
        List of SentimentResult in the same order.
        """
        return [self.classify(t) for t in texts]

    def _assign_label(self, score: float) -> str:
        """Assign label using instance thresholds."""
        if score > self.bullish_threshold:
            return _LABEL_BULLISH
        if score < self.bearish_threshold:
            return _LABEL_BEARISH
        return _LABEL_NEUTRAL

    def _compute_aspect_sentiments(
        self, text: str
    ) -> list[AspectSentiment]:
        """Compute per-aspect sentiment scores.

        Parameters
        ----------
        text:
            Preprocessed text to analyze.

        Returns
        -------
        List of AspectSentiment for each detected aspect.
        """
        aspect_results = self.aspect_detector.detect_aspects(text)
        if not aspect_results:
            return []

        # Group sentences by aspect
        aspect_sentences: dict[str, list[str]] = {}
        for aspect, sentence in aspect_results:
            aspect_sentences.setdefault(aspect, []).append(sentence)

        # Score each aspect
        aspect_sentiments: list[AspectSentiment] = []
        for aspect, sentences in sorted(aspect_sentences.items()):
            # Combine sentences for this aspect
            combined = "。".join(sentences)
            score = self.analyzer.score(combined)
            label = self._assign_label(score)
            confidence = _compute_confidence(score)

            aspect_sentiments.append(AspectSentiment(
                aspect=aspect,
                label=label,
                confidence=confidence,
            ))

        return aspect_sentiments
