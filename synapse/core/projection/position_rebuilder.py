"""Position Rebuilder — Rebuild positions from canonical Decision/Review.

ADR-009: Event-triggered rebuild.
- Decision.recorded → create/update Position
- Decision.sold → close Position
- Review.completed → update Position.research_state

Positions are projections — deletable and rebuildable from canonical artifacts.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from synapse.core.schemas.base import ObjectStatus
from synapse.core.schemas.decision import Decision, DecisionType
from synapse.core.schemas.position import (
    AttentionState,
    Position,
    ResearchState,
    ThesisStatus,
)
from synapse.core.schemas.review import Review, ReviewOutcome
from synapse.core.identity import SecurityIdentity


def _security_key(decision: Decision) -> str:
    """Derive a stable security key from a Decision."""
    return SecurityIdentity.from_ticker(
        market=decision.market, exchange="sh" if decision.ticker.startswith("6") else "sz", ticker=decision.ticker
    ).security_id


def _apply_decision(positions: dict[str, Position], decision: Decision) -> None:
    """Apply a single Decision to the positions dict (in-place).

    Rules (from ADR-009):
    - Decision.recorded → create or update Position
    - Decision.sold → close Position
    """
    key = _security_key(decision)

    if decision.decision_type == DecisionType.BUY:
        if key in positions:
            # Update existing position
            pos = positions[key]
            pos.current_shares += 1  # P1: simplified — just mark as held
            pos.linked_decision_id = decision.id
        else:
            # Create new position
            positions[key] = Position(
                id=f"pos_{decision.ticker}",
                ticker=decision.ticker,
                symbol=decision.symbol,
                market=decision.market,
                linked_thesis_id=decision.linked_thesis_id,
                thesis_at_entry=decision.thesis,
                entry_date=decision.created_at.date(),
                current_shares=1,
                research_state=ResearchState(
                    thesis_status=ThesisStatus.ACTIVE,
                    attention_state=AttentionState.STABLE,
                ),
                linked_decision_id=decision.id,
            )
    elif decision.decision_type == DecisionType.SELL:
        if key in positions:
            positions[key].status = ObjectStatus.ARCHIVED
            positions[key].research_state.thesis_status = ThesisStatus.INVALIDATED


def _apply_review(positions: dict[str, Review], review: Review) -> None:
    """Apply a Review to update position research state."""
    # Reviews are keyed by linked_decision_id for lookup
    pass  # Reviews are handled via position lookup in rebuild_from_decisions


def rebuild_from_decisions(
    decisions: list[Decision],
    reviews: Optional[list[Review]] = None,
) -> list[Position]:
    """Rebuild all positions from a list of Decisions (and optional Reviews).

    This is the core projection function. It replays Decision events
    to reconstruct current Position state.

    Args:
        decisions: All decisions, sorted by created_at ascending.
        reviews: Optional reviews to update research_state.

    Returns:
        List of active Position objects.
    """
    positions: dict[str, Position] = {}

    # Sort decisions chronologically
    sorted_decisions = sorted(decisions, key=lambda d: d.created_at)

    for decision in sorted_decisions:
        _apply_decision(positions, decision)

    # Apply reviews if provided
    if reviews:
        review_map: dict[str, Review] = {}
        for review in reviews:
            if review.linked_decision_id:
                review_map[review.linked_decision_id] = review

        for key, pos in positions.items():
            if pos.linked_decision_id and pos.linked_decision_id in review_map:
                review = review_map[pos.linked_decision_id]
                if review.review_outcome == ReviewOutcome.THESIS_CONFIRMED:
                    pos.research_state.thesis_status = ThesisStatus.ACTIVE
                elif review.review_outcome == ReviewOutcome.PARTIALLY_CONFIRMED:
                    pos.research_state.thesis_status = ThesisStatus.WEAKENED
                elif review.review_outcome == ReviewOutcome.THESIS_INVALIDATED:
                    pos.research_state.thesis_status = ThesisStatus.INVALIDATED
                pos.research_state.last_review_date = review.created_at.date()

    # Return only active positions
    return [pos for pos in positions.values() if pos.status == ObjectStatus.ACTIVE]


def save_positions(positions: list[Position], output_dir: str | Path) -> list[Path]:
    """Save rebuilt positions to YAML files.

    Args:
        positions: List of Position objects to save.
        output_dir: Directory to write position files (typically workspace/positions/current/).

    Returns:
        List of paths written.
    """
    from synapse.core.loader import save_object
    from synapse.core.naming import position_filename

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for pos in positions:
        filename = position_filename(market=pos.market, symbol=pos.ticker)
        path = output_dir / filename
        save_object(pos, path)
        paths.append(path)

    return paths
