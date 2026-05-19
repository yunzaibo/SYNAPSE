"""Lexicon Loader -- YAML-based sentiment lexicon loading and validation.

Loads the financial sentiment lexicon from YAML files, validates the schema,
and provides in-memory caching for fast repeated access.

Part of P4 Chinese Financial NLP Layer (F-044).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Default lexicon path relative to this file
_DEFAULT_LEXICON_PATH = Path(__file__).parent / "sentiment_dict.yaml"

# Required fields for each term entry
_REQUIRED_TERM_FIELDS: frozenset[str] = frozenset({
    "term", "sentiment", "score", "category", "negation_sensitive",
})

# Valid sentiment values
_VALID_SENTIMENTS: frozenset[str] = frozenset({"bullish", "bearish", "neutral"})

# Valid categories
_VALID_CATEGORIES: frozenset[str] = frozenset({
    "growth", "decline", "risk", "opportunity", "market", "regulatory", "neutral",
})

# Score range
_SCORE_MIN: float = -1.0
_SCORE_MAX: float = 1.0


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TermEntry:
    """A single sentiment term entry from the lexicon.

    Attributes
    ----------
    term:
        The Chinese financial term (e.g. "扭亏为盈").
    sentiment:
        Sentiment polarity: "bullish", "bearish", or "neutral".
    score:
        Sentiment score in [-1.0, 1.0].
    category:
        Domain category (growth, decline, risk, opportunity, market, regulatory, neutral).
    negation_sensitive:
        Whether this term's sentiment should be flipped when negated.
    context_window:
        Number of characters to scan for negation/degree markers (default 3).
    """

    term: str = ""
    sentiment: str = "neutral"
    score: float = 0.0
    category: str = "neutral"
    negation_sensitive: bool = False
    context_window: int = 3

    def to_dict(self) -> dict:
        return {
            "term": self.term,
            "sentiment": self.sentiment,
            "score": self.score,
            "category": self.category,
            "negation_sensitive": self.negation_sensitive,
            "context_window": self.context_window,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TermEntry:
        return cls(
            term=data.get("term", ""),
            sentiment=data.get("sentiment", "neutral"),
            score=float(data.get("score", 0.0)),
            category=data.get("category", "neutral"),
            negation_sensitive=bool(data.get("negation_sensitive", False)),
            context_window=int(data.get("context_window", 3)),
        )


# ---------------------------------------------------------------------------
# Lexicon Metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LexiconMeta:
    """Metadata about a loaded lexicon.

    Attributes
    ----------
    version:
        Lexicon version string.
    description:
        Human-readable description.
    total_terms:
        Total number of terms loaded.
    category_counts:
        Number of terms per category.
    load_time_ms:
        Time taken to load and parse the lexicon in milliseconds.
    """

    version: str = ""
    description: str = ""
    total_terms: int = 0
    category_counts: dict[str, int] = field(default_factory=dict)
    load_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "description": self.description,
            "total_terms": self.total_terms,
            "category_counts": dict(self.category_counts),
            "load_time_ms": self.load_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LexiconMeta:
        return cls(
            version=data.get("version", ""),
            description=data.get("description", ""),
            total_terms=int(data.get("total_terms", 0)),
            category_counts=data.get("category_counts", {}),
            load_time_ms=float(data.get("load_time_ms", 0.0)),
        )


# ---------------------------------------------------------------------------
# Schema Validation
# ---------------------------------------------------------------------------

class LexiconValidationError(ValueError):
    """Raised when lexicon YAML fails schema validation."""


def validate_term(data: dict, index: int) -> TermEntry:
    """Validate a single term entry and return a TermEntry.

    Parameters
    ----------
    data:
        Raw dict from YAML.
    index:
        Index of the term in the list (for error messages).

    Returns
    -------
    Validated TermEntry.

    Raises
    ------
    LexiconValidationError
        If required fields are missing or values are out of range.
    """
    # Check required fields
    missing = _REQUIRED_TERM_FIELDS - set(data.keys())
    if missing:
        raise LexiconValidationError(
            f"Term at index {index} missing required fields: {missing}"
        )

    # Validate sentiment
    sentiment = data.get("sentiment", "")
    if sentiment not in _VALID_SENTIMENTS:
        raise LexiconValidationError(
            f"Term at index {index} has invalid sentiment '{sentiment}': "
            f"must be one of {_VALID_SENTIMENTS}"
        )

    # Validate score range
    score = float(data.get("score", 0.0))
    if not (_SCORE_MIN <= score <= _SCORE_MAX):
        raise LexiconValidationError(
            f"Term at index {index} has score {score} out of range "
            f"[{_SCORE_MIN}, {_SCORE_MAX}]"
        )

    # Validate category
    category = data.get("category", "")
    if category not in _VALID_CATEGORIES:
        raise LexiconValidationError(
            f"Term at index {index} has invalid category '{category}': "
            f"must be one of {_VALID_CATEGORIES}"
        )

    return TermEntry.from_dict(data)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LexiconLoader:
    """YAML-based sentiment lexicon loader with validation and caching.

    Usage::

        loader = LexiconLoader()
        terms, meta = loader.load()  # loads default lexicon
        terms, meta = loader.load("custom_lexicon.yaml")  # custom path

    Attributes
    ----------
    cache:
        In-memory cache of loaded terms keyed by file path.
    """

    cache: dict[str, tuple[dict[str, TermEntry], LexiconMeta]] = field(
        default_factory=dict
    )

    def load(
        self, path: Optional[str | Path] = None
    ) -> tuple[dict[str, TermEntry], LexiconMeta]:
        """Load and validate a sentiment lexicon from YAML.

        Parameters
        ----------
        path:
            Path to the YAML lexicon file. If None, uses the default
            bundled lexicon.

        Returns
        -------
        Tuple of (terms_dict, metadata).

        Raises
        ------
        LexiconValidationError
            If the YAML content fails schema validation.
        FileNotFoundError
            If the specified file does not exist.
        """
        file_path = Path(path) if path else _DEFAULT_LEXICON_PATH
        cache_key = str(file_path.resolve())

        # Return cached result if available
        if cache_key in self.cache:
            return self.cache[cache_key]

        start_time = time.monotonic()

        # Read and parse YAML
        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict) or "terms" not in raw:
            raise LexiconValidationError(
                f"Invalid lexicon structure: expected dict with 'terms' key, "
                f"got {type(raw).__name__}"
            )

        terms_list = raw["terms"]
        if not isinstance(terms_list, list):
            raise LexiconValidationError(
                f"Expected 'terms' to be a list, got {type(terms_list).__name__}"
            )

        # Validate and build terms dict
        terms_dict: dict[str, TermEntry] = {}
        category_counts: dict[str, int] = {}

        for i, term_data in enumerate(terms_list):
            entry = validate_term(term_data, i)
            terms_dict[entry.term] = entry
            category_counts[entry.category] = category_counts.get(entry.category, 0) + 1

        elapsed_ms = (time.monotonic() - start_time) * 1000

        meta = LexiconMeta(
            version=raw.get("version", ""),
            description=raw.get("description", ""),
            total_terms=len(terms_dict),
            category_counts=category_counts,
            load_time_ms=round(elapsed_ms, 2),
        )

        # Cache the result
        self.cache[cache_key] = (terms_dict, meta)

        logger.info(
            "Loaded %d terms from %s in %.1fms",
            meta.total_terms,
            file_path,
            meta.load_time_ms,
        )

        return terms_dict, meta

    def load_terms(self, path: Optional[str | Path] = None) -> dict[str, TermEntry]:
        """Load only the terms dict (convenience method).

        Parameters
        ----------
        path:
            Path to the YAML lexicon file.

        Returns
        -------
        Dict mapping term strings to TermEntry objects.
        """
        terms, _ = self.load(path)
        return terms

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self.cache.clear()

    def add_custom_terms(
        self, terms_dict: dict[str, TermEntry], custom_terms: list[dict]
    ) -> dict[str, TermEntry]:
        """Add custom terms to an existing terms dict.

        Parameters
        ----------
        terms_dict:
            Existing terms dict to extend.
        custom_terms:
            List of raw dicts with term entries.

        Returns
        -------
        Updated terms dict (mutated in place).
        """
        for i, term_data in enumerate(custom_terms):
            entry = validate_term(term_data, len(terms_dict) + i)
            terms_dict[entry.term] = entry
        return terms_dict
