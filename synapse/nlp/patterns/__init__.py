"""Financial Patterns -- Regex patterns for financial metric extraction.

Part of P4 Chinese Financial NLP Layer (F-037).
"""

from __future__ import annotations

__all__ = [
    "METRIC_PATTERNS",
    "ALL_PATTERNS",
    "APPROXIMATION_PATTERN",
    "NumberPattern",
    "detect_period",
    "extract_approximation_markers",
]

from synapse.nlp.patterns.financial_patterns import (
    METRIC_PATTERNS,
    ALL_PATTERNS,
    APPROXIMATION_PATTERN,
    NumberPattern,
    detect_period,
    extract_approximation_markers,
)
