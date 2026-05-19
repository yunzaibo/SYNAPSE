"""Score Aggregator — Weighted sum aggregation with auto-normalization.

Implements the 4-dimension weighted sum formula:
  total_score = w_signal * s_signal + w_event * s_event + w_portfolio * s_portfolio + w_market * s_market

Default weights: signal=0.35, event=0.30, portfolio=0.20, market=0.15
Missing data contributes 0.0 (except market: 0.5 neutral).
Auto-normalizes weights to sum to 1.0 when they don't.
"""

from __future__ import annotations

import logging
import warnings
from typing import Optional

logger = logging.getLogger(__name__)

# Default dimension weights — must sum to 1.0
DEFAULT_WEIGHTS: dict[str, float] = {
    "signal": 0.35,
    "event": 0.30,
    "portfolio": 0.20,
    "market": 0.15,
}

# Neutral score for missing market data (not 0.0, because absence of
# market info should not penalize a stock)
MARKET_NEUTRAL: float = 0.5


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Normalize weights to sum to 1.0.

    If weights already sum to 1.0 (within floating-point tolerance),
    returns them unchanged. Otherwise, normalizes and emits a warning.

    Args:
        weights: Dimension name -> weight mapping.

    Returns:
        Normalized weights summing to 1.0.
    """
    total = sum(weights.values())
    if abs(total - 1.0) < 1e-9:
        return dict(weights)

    warnings.warn(
        f"Weights sum to {total:.4f}, not 1.0 — normalizing automatically",
        UserWarning,
        stacklevel=2,
    )
    logger.warning("Weights sum to %.4f, not 1.0 — normalizing automatically", total)

    return {k: v / total for k, v in weights.items()}


def aggregate_scores(
    component_scores: dict[str, float],
    weights: Optional[dict[str, float]] = None,
) -> float:
    """Compute weighted sum of component scores.

    Args:
        component_scores: Dimension name -> score in [0.0, 1.0].
                          Missing dimensions contribute 0.0.
                          Missing "market" contributes MARKET_NEUTRAL (0.5).
        weights: Dimension name -> weight. Defaults to DEFAULT_WEIGHTS.
                 Auto-normalized if sum != 1.0.

    Returns:
        Total score in [0.0, 1.0].
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    weights = normalize_weights(weights)

    total = 0.0
    for dim, w in weights.items():
        score = component_scores.get(dim)
        if score is None:
            # Missing data: 0.0 for all dimensions except market
            if dim == "market":
                score = MARKET_NEUTRAL
            else:
                score = 0.0
        total += w * score

    # Clamp to [0.0, 1.0] for safety
    return max(0.0, min(1.0, total))


def build_reason(component_scores: dict[str, float], weights: dict[str, float]) -> str:
    """Build a human-readable reason string from component scores.

    Lists each dimension with its score and weight, then the total.
    """
    parts = []
    for dim in ["signal", "event", "portfolio", "market"]:
        score = component_scores.get(dim)
        w = weights.get(dim, 0.0)
        if score is None:
            if dim == "market":
                score_str = f"{MARKET_NEUTRAL:.2f} (neutral)"
            else:
                score_str = "N/A"
        else:
            score_str = f"{score:.2f}"
        parts.append(f"{dim}={score_str}*{w:.2f}")

    return ", ".join(parts)
