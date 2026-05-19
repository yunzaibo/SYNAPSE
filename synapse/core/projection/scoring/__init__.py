"""Scoring Engine — 4-dimension weighted sum model for watchlist priority.

Components:
- engine: ScoringEngine with pipeline architecture
- types: ScoredEntry, ScoringResult, ScoringContext, MarketData
- aggregator: aggregate_scores() with weighted sum formula
- event_scorer: decay-aware event scoring
- portfolio_scorer: portfolio-aware boost scoring
"""

from synapse.core.projection.scoring.engine import ScoringEngine
from synapse.core.projection.scoring.types import (
    MarketData,
    ScoredEntry,
    ScoringContext,
    ScoringResult,
)
from synapse.core.projection.scoring.aggregator import (
    aggregate_scores,
    DEFAULT_WEIGHTS,
    normalize_weights,
)
from synapse.core.projection.scoring.event_scorer import (
    DecayScore,
    score_event_decay,
)
from synapse.core.projection.scoring.portfolio_scorer import (
    ThesisAttentionMap,
    build_thesis_attention_map,
    score_portfolio_boost,
)
from synapse.core.projection.scoring.market_scorer import score_market_context

__all__ = [
    "ScoringEngine",
    "ScoredEntry",
    "ScoringResult",
    "ScoringContext",
    "MarketData",
    "aggregate_scores",
    "DEFAULT_WEIGHTS",
    "normalize_weights",
    "DecayScore",
    "score_event_decay",
    "ThesisAttentionMap",
    "build_thesis_attention_map",
    "score_portfolio_boost",
    "score_market_context",
]
