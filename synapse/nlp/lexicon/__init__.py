"""NLP Lexicon -- Financial sentiment lexicon with negation and degree support.

Provides LexiconLoader, EnhancedLexiconAnalyzer, NegationDetector,
DegreeModifier, and the default 500+ term Chinese financial sentiment
lexicon in YAML format.

Part of P4 Chinese Financial NLP Layer (F-044).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from synapse.nlp.lexicon.degree import DegreeLevel, DegreeModifier, DegreeResult
    from synapse.nlp.lexicon.loader import LexiconLoader, LexiconMeta, TermEntry
    from synapse.nlp.lexicon.negation import NegationDetector, NegationResult
    from synapse.nlp.lexicon.scorer import EnhancedLexiconAnalyzer, ScoreBreakdown

__all__ = [
    # Loader
    "LexiconLoader",
    "LexiconMeta",
    "TermEntry",
    # Negation
    "NegationDetector",
    "NegationResult",
    # Degree
    "DegreeModifier",
    "DegreeLevel",
    "DegreeResult",
    # Scorer
    "EnhancedLexiconAnalyzer",
    "ScoreBreakdown",
]


def __getattr__(name: str):
    if name in ("LexiconLoader", "LexiconMeta", "TermEntry"):
        from synapse.nlp.lexicon.loader import LexiconLoader, LexiconMeta, TermEntry
        _map = {"LexiconLoader": LexiconLoader, "LexiconMeta": LexiconMeta, "TermEntry": TermEntry}
        return _map[name]
    if name in ("NegationDetector", "NegationResult"):
        from synapse.nlp.lexicon.negation import NegationDetector, NegationResult
        _map = {"NegationDetector": NegationDetector, "NegationResult": NegationResult}
        return _map[name]
    if name in ("DegreeModifier", "DegreeLevel", "DegreeResult"):
        from synapse.nlp.lexicon.degree import DegreeLevel, DegreeModifier, DegreeResult
        _map = {"DegreeModifier": DegreeModifier, "DegreeLevel": DegreeLevel, "DegreeResult": DegreeResult}
        return _map[name]
    if name in ("EnhancedLexiconAnalyzer", "ScoreBreakdown"):
        from synapse.nlp.lexicon.scorer import EnhancedLexiconAnalyzer, ScoreBreakdown
        _map = {"EnhancedLexiconAnalyzer": EnhancedLexiconAnalyzer, "ScoreBreakdown": ScoreBreakdown}
        return _map[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
