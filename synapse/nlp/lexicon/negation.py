"""Negation Detection -- Context window-based negation for Chinese financial text.

Detects negation markers (不/未/没/非/无) within a configurable token window
before sentiment-bearing terms, flipping their polarity.

Part of P4 Chinese Financial NLP Layer (F-044).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Chinese negation markers ordered by commonality
NEGATION_MARKERS: tuple[str, ...] = (
    "不", "没", "未", "非", "无",
    "没有", "无法", "未能", "不曾", "尚未",
    "并非", "不用", "不必", "不要", "不会",
    "不准", "不足", "不够", "不力",
)

# Characters that follow single-char negation markers to form non-negation words.
# e.g. "非" + "常" = "非常" (intensifier, not negation)
# e.g. "不" + "但" = "不但" (conjunction, not negation)
_SINGLE_CHAR_FOLLOW_EXCLUSIONS: dict[str, frozenset[str]] = {
    "非": frozenset({"常", "凡", "洲", "属"}),
    "不": frozenset({
        "但", "过", "仅", "得", "管", "论", "及", "若", "然", "如",
        "堪", "妨", "屑", "齿", "甘", "胜", "忍", "肯", "易", "可",
        "必", "曾", "再", "复", "且", "遂", "虞", "至", "适", "遑",
        "甯", "彀", "够", "怎", "几", "少", "赖", "逮", "迭", "宁",
    }),
    "没": frozenset({"有", "收", "落", "完", "了", "准", "谱", "劲"}),
    "未": frozenset({
        "来", "必", "免", "曾", "然", "经", "及", "可", "定", "知",
        "能", "遂", "央", "艾", "萌", "几", "亡", "已", "竟", "妨",
        "属", "了", "满", "尽",
    }),
    "无": frozenset({
        "法", "力", "比", "论", "偿", "关", "需", "从", "缘", "奈",
        "形", "数", "穷", "私", "辜", "聊",
    }),
}

# Compiled pattern for negation markers (longest first to avoid partial matches)
_NEGATION_PATTERN = re.compile(
    "|".join(re.escape(m) for m in sorted(NEGATION_MARKERS, key=len, reverse=True))
)

# Default context window size (number of characters/tokens)
DEFAULT_WINDOW_SIZE: int = 3


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class NegationResult:
    """Result of negation detection for a single term in text.

    Attributes
    ----------
    term:
        The sentiment term that was analyzed.
    term_start:
        Character offset where the term starts in the text.
    negated:
        Whether a negation marker was found within the context window.
    marker:
        The negation marker that was detected (empty string if none).
    marker_offset:
        Character offset of the negation marker (-1 if none).
    """

    term: str = ""
    term_start: int = 0
    negated: bool = False
    marker: str = ""
    marker_offset: int = -1

    def to_dict(self) -> dict:
        return {
            "term": self.term,
            "term_start": self.term_start,
            "negated": self.negated,
            "marker": self.marker,
            "marker_offset": self.marker_offset,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NegationResult:
        return cls(
            term=data.get("term", ""),
            term_start=int(data.get("term_start", 0)),
            negated=bool(data.get("negated", False)),
            marker=data.get("marker", ""),
            marker_offset=int(data.get("marker_offset", -1)),
        )


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class NegationDetector:
    """Context window-based negation detector for Chinese financial text.

    Scans a configurable character window before each sentiment term
    for negation markers. When found, the term's sentiment polarity is flipped.

    Single-character markers are validated against exclusion lists to avoid
    false positives (e.g. "非" in "非常" should not be treated as negation).

    Attributes
    ----------
    window_size:
        Number of characters to scan before the term (default 3).
    markers:
        Tuple of negation marker strings to detect.
    """

    window_size: int = DEFAULT_WINDOW_SIZE
    markers: tuple[str, ...] = NEGATION_MARKERS

    def detect(self, text: str, term: str, term_start: int) -> NegationResult:
        """Detect whether a term is negated in the given text.

        Parameters
        ----------
        text:
            Full text content to search within.
        term:
            The sentiment term to check for negation.
        term_start:
            Character offset where the term starts in the text.

        Returns
        -------
        NegationResult with negation status and marker details.
        """
        if not text or not term or term_start < 0:
            return NegationResult(term=term, term_start=term_start)

        # Define the context window: characters before the term
        window_start = max(0, term_start - self.window_size)
        context = text[window_start:term_start]

        if not context:
            return NegationResult(term=term, term_start=term_start)

        # Search for negation markers in the context window
        # Sort markers by length descending to match longest first
        sorted_markers = sorted(self.markers, key=len, reverse=True)

        for marker in sorted_markers:
            idx = context.rfind(marker)
            if idx < 0:
                continue

            # For single-char markers, check exclusion list to avoid
            # false positives (e.g. "非" in "非常")
            if len(marker) == 1:
                abs_after = window_start + idx + len(marker)
                if abs_after < len(text):
                    next_char = text[abs_after]
                    exclusions = _SINGLE_CHAR_FOLLOW_EXCLUSIONS.get(marker, frozenset())
                    if next_char in exclusions:
                        continue

            # Found a valid negation marker; compute its absolute offset
            absolute_offset = window_start + idx
            return NegationResult(
                term=term,
                term_start=term_start,
                negated=True,
                marker=marker,
                marker_offset=absolute_offset,
            )

        return NegationResult(term=term, term_start=term_start)

    def detect_all(self, text: str, term_positions: list[tuple[str, int]]) -> list[NegationResult]:
        """Detect negation for multiple terms in a text.

        Parameters
        ----------
        text:
            Full text content.
        term_positions:
            List of (term, start_offset) tuples.

        Returns
        -------
        List of NegationResult, one per term.
        """
        return [self.detect(text, term, pos) for term, pos in term_positions]

    def is_negated(self, text: str, term: str, term_start: int) -> bool:
        """Quick boolean check: is this term negated?

        Parameters
        ----------
        text:
            Full text content.
        term:
            The sentiment term.
        term_start:
            Character offset of the term.

        Returns
        -------
        True if a negation marker is found in the context window.
        """
        return self.detect(text, term, term_start).negated
