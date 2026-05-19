"""Scoring Engine — Pipeline architecture for watchlist entry scoring.

The engine registers scoring functions (one per dimension), runs them
in order, and aggregates results via weighted sum.

Pipeline:
  WatchlistEntry + ScoringContext -> ScoringFunction -> (float, str)
  -> aggregate_scores() -> ScoredEntry
  -> all ScoredEntries -> ScoringResult

Design:
  - Deterministic: identical inputs always produce identical outputs.
  - Pluggable: new dimensions added by registering a ScoringFunction.
  - Transparent: every ScoredEntry carries its component breakdown.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date
from typing import Callable, Optional

from synapse.core.projection.scoring.aggregator import (
    DEFAULT_WEIGHTS,
    aggregate_scores,
    build_reason,
    normalize_weights,
)
from synapse.core.projection.scoring.event_scorer import score_event_decay
from synapse.core.projection.scoring.market_scorer import score_market_context
from synapse.core.projection.scoring.portfolio_scorer import (
    build_thesis_attention_map,
    score_portfolio_boost,
)
from synapse.core.projection.scoring.types import (
    MarketData,
    ScoredEntry,
    ScoringContext,
    ScoringResult,
)
from synapse.core.schemas.watchlist import WatchlistEntry

logger = logging.getLogger(__name__)

# ScoringFunction signature: (entry, context) -> (score, reason)
ScoringFunction = Callable[[WatchlistEntry, ScoringContext], tuple[float, str]]


def _score_signal(entry: WatchlistEntry, ctx: ScoringContext) -> tuple[float, str]:
    """Score based on signal strength and count.

    More signals and stronger signals yield higher scores.
    """
    relevant = [s for s in ctx.signals if entry.ticker in s.related_tickers]
    if not relevant:
        return 0.0, "no signals"

    # Strength mapping: weak=0.3, medium=0.6, strong=1.0
    strength_map = {"weak": 0.3, "medium": 0.6, "strong": 1.0}
    max_strength = 0.0
    for sig in relevant:
        val = strength_map.get(sig.strength.value, 0.5)
        if val > max_strength:
            max_strength = val

    # Bonus for multiple signals (diminishing returns)
    count_bonus = min(len(relevant) * 0.1, 0.3)
    score = min(max_strength + count_bonus, 1.0)

    reason = f"{len(relevant)} signal(s), strongest={max_strength:.1f}"
    return score, reason


def _score_portfolio(entry: WatchlistEntry, ctx: ScoringContext) -> tuple[float, str]:
    """Score based on portfolio position state.

    Uses thesis_status AND attention_state from Position.research_state.
    Thesis status boosts: INVALIDATED (0.5) > WEAKENED (0.35) > ACTIVE (0.15).
    Attention state boosts: RISING (0.25) > FADING (0.10) > STABLE (0.05).
    Missing positions contribute 0.0.
    """
    thesis_attention_map = build_thesis_attention_map(ctx.positions)
    return score_portfolio_boost(entry.ticker, thesis_attention_map)


class ScoringEngine:
    """Pipeline-based scoring engine for watchlist entries.

    Registers scoring functions for each dimension, runs them in order,
    and aggregates results via weighted sum.

    Usage:
        engine = ScoringEngine()
        result = engine.score(entries, context)
        for scored in result.entries:
            print(f"{scored.entry.ticker}: {scored.total_score:.2f}")
    """

    def __init__(self, weights: Optional[dict[str, float]] = None) -> None:
        """Initialize the scoring engine.

        Args:
            weights: Dimension weights. Defaults to DEFAULT_WEIGHTS.
                     Auto-normalized if sum != 1.0.
        """
        self._weights = normalize_weights(weights or dict(DEFAULT_WEIGHTS))
        self._scoring_functions: dict[str, ScoringFunction] = {}

        # Register built-in scoring functions
        self.register("signal", _score_signal)
        self.register("event", score_event_decay)
        self.register("portfolio", _score_portfolio)
        self.register("market", score_market_context)

    @property
    def weights(self) -> dict[str, float]:
        """Current dimension weights (normalized)."""
        return dict(self._weights)

    @property
    def dimensions(self) -> list[str]:
        """Registered dimension names."""
        return list(self._scoring_functions.keys())

    def register(self, dimension: str, func: ScoringFunction) -> None:
        """Register a scoring function for a dimension.

        Args:
            dimension: Dimension name (must match a weight key).
            func: Scoring function (entry, context) -> (score, reason).
        """
        self._scoring_functions[dimension] = func

    def unregister(self, dimension: str) -> None:
        """Remove a scoring function for a dimension.

        Args:
            dimension: Dimension name to remove.
        """
        self._scoring_functions.pop(dimension, None)

    def _compute_config_hash(self) -> str:
        """Compute a hash of the engine configuration for traceability."""
        config_str = f"weights={sorted(self._weights.items())},dims={sorted(self._scoring_functions.keys())}"
        return hashlib.sha256(config_str.encode()).hexdigest()[:12]

    def score(
        self,
        entries: list[WatchlistEntry],
        context: ScoringContext,
    ) -> ScoringResult:
        """Score a batch of watchlist entries.

        Args:
            entries: Watchlist entries to score.
            context: Scoring context with all data sources.

        Returns:
            ScoringResult with scored entries and metadata.
        """
        scored_entries: list[ScoredEntry] = []

        for entry in entries:
            component_scores: dict[str, float] = {}
            reasons: list[str] = []

            for dim, func in self._scoring_functions.items():
                score, reason = func(entry, context)
                component_scores[dim] = score
                reasons.append(f"{dim}: {reason}")

            total = aggregate_scores(component_scores, self._weights)
            reason_str = build_reason(component_scores, self._weights)

            scored = ScoredEntry(
                entry=entry,
                total_score=total,
                component_scores=component_scores,
                reason=reason_str,
            )
            scored_entries.append(scored)

        # Sort by total_score descending (highest priority first)
        scored_entries.sort(key=lambda s: s.total_score, reverse=True)

        return ScoringResult(
            entries=scored_entries,
            target_date=context.target_date,
            config_hash=self._compute_config_hash(),
        )

    def score_single(
        self,
        entry: WatchlistEntry,
        context: ScoringContext,
    ) -> ScoredEntry:
        """Score a single watchlist entry.

        Convenience method for scoring one entry without batch overhead.

        Args:
            entry: Watchlist entry to score.
            context: Scoring context with all data sources.

        Returns:
            ScoredEntry with score and breakdown.
        """
        result = self.score([entry], context)
        return result.entries[0]
