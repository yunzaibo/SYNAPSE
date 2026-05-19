"""Enhanced Lexicon Scorer -- Negation-aware, degree-modified sentiment scoring.

Extends the base LexiconAnalyzer from synapse/event/social.py with:
- YAML-based lexicon loading via LexiconLoader
- Negation detection (不/未/没/非/无 + context window)
- Degree modifier handling (strong=1.5x, moderate=1.0x, weak=0.5x)
- Custom term support
- Category-level score aggregation

Part of P4 Chinese Financial NLP Layer (F-044).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from synapse.event.social import LexiconAnalyzer

from synapse.nlp.lexicon.degree import DegreeLevel, DegreeModifier, DegreeResult
from synapse.nlp.lexicon.loader import LexiconLoader, LexiconMeta, TermEntry
from synapse.nlp.lexicon.negation import NegationDetector, NegationResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Score Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Detailed breakdown of a sentiment scoring operation.

    Attributes
    ----------
    text:
        The original text that was scored.
    raw_score:
        Aggregate score before normalization.
    final_score:
        Normalized score in [-1.0, 1.0].
    matched_terms:
        List of (term, base_score, negated, degree_multiplier) tuples.
    negation_flips:
        Number of terms whose polarity was flipped by negation.
    degree_adjustments:
        Number of terms whose score was modified by degree modifiers.
    """

    text: str = ""
    raw_score: float = 0.0
    final_score: float = 0.0
    matched_terms: tuple[tuple[str, float, bool, float], ...] = ()
    negation_flips: int = 0
    degree_adjustments: int = 0

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "raw_score": self.raw_score,
            "final_score": self.final_score,
            "matched_terms": [
                {"term": t, "score": s, "negated": n, "multiplier": m}
                for t, s, n, m in self.matched_terms
            ],
            "negation_flips": self.negation_flips,
            "degree_adjustments": self.degree_adjustments,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScoreBreakdown:
        matched = [
            (t["term"], t["score"], t["negated"], t["multiplier"])
            for t in data.get("matched_terms", [])
        ]
        return cls(
            text=data.get("text", ""),
            raw_score=float(data.get("raw_score", 0.0)),
            final_score=float(data.get("final_score", 0.0)),
            matched_terms=tuple(matched),
            negation_flips=int(data.get("negation_flips", 0)),
            degree_adjustments=int(data.get("degree_adjustments", 0)),
        )


# ---------------------------------------------------------------------------
# Enhanced Analyzer
# ---------------------------------------------------------------------------

@dataclass
class EnhancedLexiconAnalyzer(LexiconAnalyzer):
    """Enhanced sentiment analyzer with negation and degree awareness.

    Extends LexiconAnalyzer with:
    - YAML-based lexicon loading via LexiconLoader
    - Negation detection (flips bullish/bearish polarity)
    - Degree modifier handling (scales score by multiplier)
    - Category-level score breakdown
    - Custom term support

    Usage::

        analyzer = EnhancedLexiconAnalyzer()
        score = analyzer.score("不看好茅台，业绩超预期")  # negation-aware
        breakdown = analyzer.score_with_breakdown("非常看好茅台")

    Attributes
    ----------
    _terms:
        Loaded term entries from YAML lexicon.
    _meta:
        Lexicon metadata.
    _negation:
        Negation detector instance.
    _degree:
        Degree modifier detector instance.
    _negation_terms:
        Set of terms that are negation-sensitive (for fast lookup).
    """

    _terms: dict[str, TermEntry] = field(default_factory=dict)
    _meta: LexiconMeta = field(default_factory=LexiconMeta)
    _negation: NegationDetector = field(default_factory=NegationDetector)
    _degree: DegreeModifier = field(default_factory=DegreeModifier)
    _negation_terms: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Load default lexicon if not already loaded."""
        if not self._terms:
            self._load_default_lexicon()

    def _load_default_lexicon(self) -> None:
        """Load the default bundled lexicon."""
        try:
            loader = LexiconLoader()
            self._terms, self._meta = loader.load()
            self._negation_terms = {
                term for term, entry in self._terms.items()
                if entry.negation_sensitive
            }
            # Also populate parent class lexicons for backward compatibility
            pos_terms = [t for t, e in self._terms.items() if e.sentiment == "bullish"]
            neg_terms = [t for t, e in self._terms.items() if e.sentiment == "bearish"]
            super().__init__(
                positive_lexicon=pos_terms if pos_terms else self.positive_lexicon,
                negative_lexicon=neg_terms if neg_terms else self.negative_lexicon,
            )
        except Exception as e:
            logger.warning("Failed to load default lexicon: %s", e)
            # Fallback to parent class defaults
            super().__init__()

    @classmethod
    def from_yaml(cls, path: str) -> EnhancedLexiconAnalyzer:
        """Create an analyzer from a custom YAML lexicon file.

        Parameters
        ----------
        path:
            Path to the YAML lexicon file.

        Returns
        -------
        Configured EnhancedLexiconAnalyzer.
        """
        loader = LexiconLoader()
        terms, meta = loader.load(path)
        negation_terms = {
            term for term, entry in terms.items()
            if entry.negation_sensitive
        }
        pos_terms = [t for t, e in terms.items() if e.sentiment == "bullish"]
        neg_terms = [t for t, e in terms.items() if e.sentiment == "bearish"]
        return cls(
            positive_lexicon=pos_terms,
            negative_lexicon=neg_terms,
            _terms=terms,
            _meta=meta,
            _negation_terms=negation_terms,
        )

    @property
    def meta(self) -> LexiconMeta:
        """Lexicon metadata."""
        return self._meta

    @property
    def term_count(self) -> int:
        """Number of terms in the loaded lexicon."""
        return len(self._terms)

    def get_term(self, term: str) -> Optional[TermEntry]:
        """Look up a term entry by its string.

        Parameters
        ----------
        term:
            The Chinese financial term.

        Returns
        -------
        TermEntry if found, None otherwise.
        """
        return self._terms.get(term)

    def score(self, text: str) -> float:
        """Score text sentiment with negation and degree awareness.

        Overrides parent class score() to add:
        - Negation detection: flips polarity for negation-sensitive terms
        - Degree modifiers: scales score by intensity multiplier

        Scoring formula:
        - For each matched term: adjusted_score = base_score * negation_sign * degree_multiplier
        - Aggregate: sum(adjusted_scores) / (total_matched + 1)
        - Clamped to [-1.0, 1.0]

        Parameters
        ----------
        text:
            Chinese text to analyze.

        Returns
        -------
        float in [-1.0, 1.0]. Positive = bullish, negative = bearish.
        """
        if not text:
            return 0.0

        total_score = 0.0
        match_count = 0

        for term, entry in self._terms.items():
            idx = text.find(term)
            if idx < 0:
                continue

            base_score = entry.score
            negated = False
            degree_mult = 1.0

            # Apply negation detection if term is negation-sensitive
            if entry.negation_sensitive:
                neg_result = self._negation.detect(text, term, idx)
                if neg_result.negated:
                    base_score = -base_score
                    negated = True

            # Apply degree modifier
            deg_result = self._degree.detect(text, term, idx)
            if deg_result.level != DegreeLevel.NONE:
                degree_mult = deg_result.multiplier

            total_score += base_score * degree_mult
            match_count += 1

        # Normalize: divide by (matches + 1) to avoid division by zero
        # and to dampen the effect of many small matches
        final_score = total_score / (match_count + 1)

        # Clamp to [-1.0, 1.0]
        return max(-1.0, min(1.0, final_score))

    def score_with_breakdown(self, text: str) -> ScoreBreakdown:
        """Score text with detailed breakdown of each matched term.

        Parameters
        ----------
        text:
            Chinese text to analyze.

        Returns
        -------
        ScoreBreakdown with per-term details.
        """
        if not text:
            return ScoreBreakdown(text=text)

        total_score = 0.0
        matched: list[tuple[str, float, bool, float]] = []
        negation_flips = 0
        degree_adjustments = 0

        for term, entry in self._terms.items():
            idx = text.find(term)
            if idx < 0:
                continue

            base_score = entry.score
            negated = False
            degree_mult = 1.0

            # Apply negation detection
            if entry.negation_sensitive:
                neg_result = self._negation.detect(text, term, idx)
                if neg_result.negated:
                    base_score = -base_score
                    negated = True
                    negation_flips += 1

            # Apply degree modifier
            deg_result = self._degree.detect(text, term, idx)
            if deg_result.level != DegreeLevel.NONE:
                degree_mult = deg_result.multiplier
                degree_adjustments += 1

            adjusted = base_score * degree_mult
            total_score += adjusted
            matched.append((term, entry.score, negated, degree_mult))

        final_score = total_score / (len(matched) + 1)
        final_score = max(-1.0, min(1.0, final_score))

        return ScoreBreakdown(
            text=text,
            raw_score=total_score,
            final_score=final_score,
            matched_terms=tuple(matched),
            negation_flips=negation_flips,
            degree_adjustments=degree_adjustments,
        )

    def score_by_category(self, text: str) -> dict[str, float]:
        """Score text and break down by category.

        Parameters
        ----------
        text:
            Chinese text to analyze.

        Returns
        -------
        Dict mapping category names to their aggregate scores.
        """
        if not text:
            return {}

        category_scores: dict[str, float] = {}
        category_counts: dict[str, int] = {}

        for term, entry in self._terms.items():
            idx = text.find(term)
            if idx < 0:
                continue

            base_score = entry.score

            # Apply negation
            if entry.negation_sensitive:
                neg_result = self._negation.detect(text, term, idx)
                if neg_result.negated:
                    base_score = -base_score

            # Apply degree
            deg_result = self._degree.detect(text, term, idx)
            if deg_result.level != DegreeLevel.NONE:
                base_score *= deg_result.multiplier

            cat = entry.category
            category_scores[cat] = category_scores.get(cat, 0.0) + base_score
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Average per category
        return {
            cat: category_scores[cat] / category_counts[cat]
            for cat in category_scores
        }

    def add_term(self, entry: TermEntry) -> None:
        """Add a custom term to the lexicon at runtime.

        Parameters
        ----------
        entry:
            The term entry to add.
        """
        self._terms[entry.term] = entry
        if entry.negation_sensitive:
            self._negation_terms.add(entry.term)

        # Update parent class lexicons
        if entry.sentiment == "bullish" and entry.term not in self.positive_lexicon:
            self.positive_lexicon.append(entry.term)
        elif entry.sentiment == "bearish" and entry.term not in self.negative_lexicon:
            self.negative_lexicon.append(entry.term)

    def remove_term(self, term: str) -> bool:
        """Remove a term from the lexicon.

        Parameters
        ----------
        term:
            The term string to remove.

        Returns
        -------
        True if the term was found and removed, False otherwise.
        """
        entry = self._terms.pop(term, None)
        if entry is None:
            return False

        self._negation_terms.discard(term)

        # Update parent class lexicons
        if entry.sentiment == "bullish" and term in self.positive_lexicon:
            self.positive_lexicon.remove(term)
        elif entry.sentiment == "bearish" and term in self.negative_lexicon:
            self.negative_lexicon.remove(term)

        return True

    def list_terms(self, category: Optional[str] = None) -> list[TermEntry]:
        """List all terms, optionally filtered by category.

        Parameters
        ----------
        category:
            If provided, only return terms in this category.

        Returns
        -------
        List of TermEntry objects.
        """
        if category is None:
            return list(self._terms.values())
        return [e for e in self._terms.values() if e.category == category]
