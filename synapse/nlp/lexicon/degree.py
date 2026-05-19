"""Degree Modifier Detection -- Intensity scaling for Chinese financial sentiment.

Detects degree modifiers (非常/极其/略微) before sentiment terms and returns
a multiplier: strong (1.5x), moderate (1.0x), weak (0.5x).

Part of P4 Chinese Financial NLP Layer (F-044).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class DegreeLevel(str, Enum):
    """Degree intensity levels."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


# Strong intensifiers: amplify sentiment
STRONG_DEGREE_MARKERS: tuple[str, ...] = (
    "非常", "极其", "特别", "极度", "极为",
    "十分", "格外", "异常", "相当", "颇",
    "狠狠", "大大", "猛烈", "严重", "显著",
    "明显", "远超", "大幅", "急剧", "暴涨",
    "暴跌", "狂", "巨",
)

# Moderate intensifiers: neutral or slight adjustment
MODERATE_DEGREE_MARKERS: tuple[str, ...] = (
    "较为", "比较", "相对", "一定", "些许",
    "有所", "略有", "小幅", "温和", "适度",
)

# Weak diminishers: reduce sentiment
WEAK_DEGREE_MARKERS: tuple[str, ...] = (
    "略微", "稍", "稍有", "略微", "一点点",
    "微微", "略", "轻", "微弱", "微小",
    "一点点", "些许", "轻微",
)

# Default context window (characters before the term)
DEFAULT_DEGREE_WINDOW: int = 4


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DegreeResult:
    """Result of degree modifier detection for a single term.

    Attributes
    ----------
    term:
        The sentiment term that was analyzed.
    term_start:
        Character offset where the term starts in the text.
    level:
        Detected degree level (strong/moderate/weak/none).
    multiplier:
        Numeric multiplier for sentiment score adjustment.
    marker:
        The degree marker that was detected (empty string if none).
    marker_offset:
        Character offset of the degree marker (-1 if none).
    """

    term: str = ""
    term_start: int = 0
    level: DegreeLevel = DegreeLevel.NONE
    multiplier: float = 1.0
    marker: str = ""
    marker_offset: int = -1

    def to_dict(self) -> dict:
        return {
            "term": self.term,
            "term_start": self.term_start,
            "level": self.level.value,
            "multiplier": self.multiplier,
            "marker": self.marker,
            "marker_offset": self.marker_offset,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DegreeResult:
        return cls(
            term=data.get("term", ""),
            term_start=int(data.get("term_start", 0)),
            level=DegreeLevel(data.get("level", "none")),
            multiplier=float(data.get("multiplier", 1.0)),
            marker=data.get("marker", ""),
            marker_offset=int(data.get("marker_offset", -1)),
        )


# ---------------------------------------------------------------------------
# Multipliers
# ---------------------------------------------------------------------------

DEGREE_MULTIPLIERS: dict[DegreeLevel, float] = {
    DegreeLevel.STRONG: 1.5,
    DegreeLevel.MODERATE: 1.0,
    DegreeLevel.WEAK: 0.5,
    DegreeLevel.NONE: 1.0,
}


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DegreeModifier:
    """Degree modifier detector for Chinese financial text.

    Scans a configurable character window before each sentiment term
    for degree markers, returning a multiplier to scale the term's score.

    Attributes
    ----------
    window_size:
        Number of characters to scan before the term (default 4).
    strong_markers:
        Tuple of strong intensifier strings.
    moderate_markers:
        Tuple of moderate intensifier strings.
    weak_markers:
        Tuple of weak diminisher strings.
    """

    window_size: int = DEFAULT_DEGREE_WINDOW
    strong_markers: tuple[str, ...] = STRONG_DEGREE_MARKERS
    moderate_markers: tuple[str, ...] = MODERATE_DEGREE_MARKERS
    weak_markers: tuple[str, ...] = WEAK_DEGREE_MARKERS

    def detect(self, text: str, term: str, term_start: int) -> DegreeResult:
        """Detect degree modifier for a term in the given text.

        Parameters
        ----------
        text:
            Full text content to search within.
        term:
            The sentiment term to check for degree modifiers.
        term_start:
            Character offset where the term starts in the text.

        Returns
        -------
        DegreeResult with level, multiplier, and marker details.
        """
        if not text or not term or term_start < 0:
            return DegreeResult(term=term, term_start=term_start)

        # Define the context window: characters before the term
        window_start = max(0, term_start - self.window_size)
        context = text[window_start:term_start]

        if not context:
            return DegreeResult(term=term, term_start=term_start)

        # Check strong markers first (highest priority)
        result = self._search_markers(context, window_start, term, term_start, self.strong_markers)
        if result is not None:
            return result

        # Then moderate
        result = self._search_markers(context, window_start, term, term_start, self.moderate_markers)
        if result is not None:
            return result

        # Then weak
        result = self._search_markers(context, window_start, term, term_start, self.weak_markers)
        if result is not None:
            return result

        return DegreeResult(term=term, term_start=term_start)

    def _search_markers(
        self,
        context: str,
        window_start: int,
        term: str,
        term_start: int,
        markers: tuple[str, ...],
    ) -> DegreeResult | None:
        """Search for markers in context, returning the first (rightmost) match."""
        # Sort by length descending to match longest first
        sorted_markers = sorted(markers, key=len, reverse=True)

        for marker in sorted_markers:
            idx = context.rfind(marker)
            if idx >= 0:
                level = self._marker_to_level(marker)
                multiplier = DEGREE_MULTIPLIERS[level]
                absolute_offset = window_start + idx
                return DegreeResult(
                    term=term,
                    term_start=term_start,
                    level=level,
                    multiplier=multiplier,
                    marker=marker,
                    marker_offset=absolute_offset,
                )

        return None

    def _marker_to_level(self, marker: str) -> DegreeLevel:
        """Map a marker string to its degree level."""
        if marker in self.strong_markers:
            return DegreeLevel.STRONG
        if marker in self.moderate_markers:
            return DegreeLevel.MODERATE
        if marker in self.weak_markers:
            return DegreeLevel.WEAK
        return DegreeLevel.NONE

    def detect_all(self, text: str, term_positions: list[tuple[str, int]]) -> list[DegreeResult]:
        """Detect degree modifiers for multiple terms in a text.

        Parameters
        ----------
        text:
            Full text content.
        term_positions:
            List of (term, start_offset) tuples.

        Returns
        -------
        List of DegreeResult, one per term.
        """
        return [self.detect(text, term, pos) for term, pos in term_positions]

    def get_multiplier(self, text: str, term: str, term_start: int) -> float:
        """Quick numeric multiplier for a term's sentiment score.

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
        Multiplier float (0.5, 1.0, or 1.5).
        """
        return self.detect(text, term, term_start).multiplier
