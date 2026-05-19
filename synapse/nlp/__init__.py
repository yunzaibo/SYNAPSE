"""NLP Layer -- Chinese financial NLP components for entity recognition and text processing.

Part of P4 Chinese Financial NLP Layer (F-041).
"""

from __future__ import annotations

__all__ = [
    # Schemas (F-041)
    "TextDocument",
    "NEREntity",
    "NERResult",
    "NEREngine",
    "TextPreprocessor",
    # Lexicon (F-044)
    "EnhancedLexiconAnalyzer",
    "LexiconLoader",
    "NegationDetector",
    "DegreeModifier",
    "ScoreBreakdown",
    "TermEntry",
    # Sentiment (F-039)
    "NewsSentimentClassifier",
    "SentimentResult",
    "AspectSentiment",
    "AspectDetector",
    "AspectResult",
    # Report Summarizer (F-038)
    "ResearchReportResult",
    "ReportSummarizer",
    "ReportRating",
]


def __getattr__(name: str):
    # Schemas (F-041)
    if name == "TextDocument":
        from synapse.nlp.schemas import TextDocument
        return TextDocument
    if name == "NEREntity":
        from synapse.nlp.schemas import NEREntity
        return NEREntity
    if name == "NERResult":
        from synapse.nlp.schemas import NERResult
        return NERResult
    if name == "NEREngine":
        from synapse.nlp.ner_engine import NEREngine
        return NEREngine
    if name == "TextPreprocessor":
        from synapse.nlp.text_preprocessor import TextPreprocessor
        return TextPreprocessor
    # Lexicon (F-044)
    if name == "EnhancedLexiconAnalyzer":
        from synapse.nlp.lexicon.scorer import EnhancedLexiconAnalyzer
        return EnhancedLexiconAnalyzer
    if name == "LexiconLoader":
        from synapse.nlp.lexicon.loader import LexiconLoader
        return LexiconLoader
    if name == "NegationDetector":
        from synapse.nlp.lexicon.negation import NegationDetector
        return NegationDetector
    if name == "DegreeModifier":
        from synapse.nlp.lexicon.degree import DegreeModifier
        return DegreeModifier
    if name == "ScoreBreakdown":
        from synapse.nlp.lexicon.scorer import ScoreBreakdown
        return ScoreBreakdown
    if name == "TermEntry":
        from synapse.nlp.lexicon.loader import TermEntry
        return TermEntry
    # Sentiment (F-039)
    if name == "NewsSentimentClassifier":
        from synapse.nlp.sentiment_classifier import NewsSentimentClassifier
        return NewsSentimentClassifier
    if name == "SentimentResult":
        from synapse.nlp.sentiment_classifier import SentimentResult
        return SentimentResult
    if name == "AspectSentiment":
        from synapse.nlp.sentiment_classifier import AspectSentiment
        return AspectSentiment
    if name == "AspectDetector":
        from synapse.nlp.aspect_detector import AspectDetector
        return AspectDetector
    if name == "AspectResult":
        from synapse.nlp.aspect_detector import AspectResult
        return AspectResult
    # Report Summarizer (F-038)
    if name == "ResearchReportResult":
        from synapse.nlp.report_summarizer import ResearchReportResult
        return ResearchReportResult
    if name == "ReportSummarizer":
        from synapse.nlp.report_summarizer import ReportSummarizer
        return ReportSummarizer
    if name == "ReportRating":
        from synapse.nlp.report_patterns import ReportRating
        return ReportRating
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
