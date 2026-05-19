"""Portfolio-Aware Scoring — Boost computation from thesis status and attention state.

Combines thesis_status and attention_state into a single portfolio boost score.
Higher boost = more urgent attention needed.

ThesisStatus priority: INVALIDATED > WEAKENED > ACTIVE
AttentionState priority: RISING > FADING > STABLE

Missing positions contribute 0.0 (no boost, no penalty).
"""

from __future__ import annotations

import logging
from typing import TypeAlias

from synapse.core.schemas.position import (
    AttentionState,
    Position,
    ThesisStatus,
)

logger = logging.getLogger(__name__)

# --- Thesis status boost constants ---
THESIS_INVALIDATED_BOOST: float = 0.5
THESIS_WEAKENED_BOOST: float = 0.35
THESIS_ACTIVE_BOOST: float = 0.15

# --- Attention state boost constants ---
ATTENTION_RISING_BOOST: float = 0.25
ATTENTION_FADING_BOOST: float = 0.10
ATTENTION_STABLE_BOOST: float = 0.05

# Maximum possible boost (sum of max thesis + max attention)
MAX_BOOST: float = THESIS_INVALIDATED_BOOST + ATTENTION_RISING_BOOST

# Type alias for the portfolio awareness map
ThesisAttentionMap: TypeAlias = dict[str, tuple[ThesisStatus, AttentionState]]


def build_thesis_attention_map(positions: list[Position]) -> ThesisAttentionMap:
    """Build a ticker -> (ThesisStatus, AttentionState) map from positions.

    Args:
        positions: List of Position objects.

    Returns:
        Mapping from ticker to (thesis_status, attention_state) tuple.
    """
    result: ThesisAttentionMap = {}
    for pos in positions:
        if not pos.ticker:
            continue
        result[pos.ticker] = (
            pos.research_state.thesis_status,
            pos.research_state.attention_state,
        )
    return result


def _thesis_boost(status: ThesisStatus) -> float:
    """Map thesis status to a boost value.

    INVALIDATED > WEAKENED > ACTIVE.
    """
    mapping = {
        ThesisStatus.INVALIDATED: THESIS_INVALIDATED_BOOST,
        ThesisStatus.WEAKENED: THESIS_WEAKENED_BOOST,
        ThesisStatus.ACTIVE: THESIS_ACTIVE_BOOST,
    }
    return mapping.get(status, THESIS_ACTIVE_BOOST)


def _attention_boost(state: AttentionState) -> float:
    """Map attention state to a boost value.

    RISING > FADING > STABLE.
    """
    mapping = {
        AttentionState.RISING: ATTENTION_RISING_BOOST,
        AttentionState.FADING: ATTENTION_FADING_BOOST,
        AttentionState.STABLE: ATTENTION_STABLE_BOOST,
    }
    return mapping.get(state, ATTENTION_STABLE_BOOST)


def score_portfolio_boost(
    ticker: str,
    thesis_attention_map: ThesisAttentionMap,
) -> tuple[float, str]:
    """Compute portfolio boost score from thesis status and attention state.

    The boost is the sum of thesis_boost + attention_boost, clamped to [0.0, 1.0].

    Args:
        ticker: Stock ticker to look up.
        thesis_attention_map: Mapping of ticker -> (ThesisStatus, AttentionState).

    Returns:
        Tuple of (boost_score, reason_string).
        Missing tickers return (0.0, "not in portfolio").
    """
    if ticker not in thesis_attention_map:
        return 0.0, "not in portfolio"

    thesis_status, attention_state = thesis_attention_map[ticker]

    t_boost = _thesis_boost(thesis_status)
    a_boost = _attention_boost(attention_state)
    total = min(t_boost + a_boost, 1.0)

    reason = (
        f"thesis={thesis_status.value} (+{t_boost:.2f}), "
        f"attention={attention_state.value} (+{a_boost:.2f})"
    )
    return total, reason
