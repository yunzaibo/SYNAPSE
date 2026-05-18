"""Decision Flow — Record buy/sell decisions.

ADR-010: Logs decision.recorded to activity.jsonl.
ADR-009: Triggers position rebuild after recording.

Flow:
1. Validate decision data
2. Save decision to YAML
3. Trigger position rebuild
4. Log activity
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from synapse.core.activity import ActivityLog, ActivityType
from synapse.core.loader import save_object
from synapse.core.projection.position_rebuilder import rebuild_from_decisions, save_positions
from synapse.core.schemas.decision import Decision, DecisionType
from synapse.core.schemas.review import Review
from synapse.core.naming import decision_dir
from synapse.core.temporal import CST


@dataclass
class DecisionRecord:
    """Result of recording a decision."""

    decision: Decision
    position_rebuilt: bool = False
    activity_logged: bool = False


def record_decision(
    decision: Decision,
    existing_decisions: list[Decision],
    existing_reviews: Optional[list[Review]] = None,
    activity_log: Optional[ActivityLog] = None,
    workspace_dir: Optional[str | Path] = None,
) -> DecisionRecord:
    """Record a buy/sell decision.

    Steps:
    1. Save decision to YAML file
    2. Rebuild positions from all decisions
    3. Save rebuilt positions
    4. Log decision.recorded activity

    Args:
        decision: The decision to record.
        existing_decisions: All existing decisions (for position rebuild).
        existing_reviews: All existing reviews (for position rebuild).
        activity_log: ActivityLog to write to. If None, activity is not logged.
        workspace_dir: Workspace root directory. If None, position rebuild is skipped.

    Returns:
        DecisionRecord with the decision and rebuild status.
    """
    # Step 1: Save decision to YAML if workspace provided
    if workspace_dir is not None:
        workspace = Path(workspace_dir)
        decisions_dir = workspace / "decisions"
        date_str = decision.created_at.strftime("%Y%m%d")
        action = decision.decision_type.value
        dir_name = decision_dir(date_str, action, decision.ticker)
        decision_path = decisions_dir / dir_name / "meta.yaml"
        save_object(decision, decision_path)

    # Step 2: Rebuild positions
    position_rebuilt = False
    if workspace_dir is not None:
        all_decisions = list(existing_decisions)
        # Ensure the new decision is included
        if not any(d.id == decision.id for d in all_decisions):
            all_decisions.append(decision)

        positions = rebuild_from_decisions(
            decisions=all_decisions,
            reviews=existing_reviews,
        )

        positions_dir = Path(workspace_dir) / "positions" / "current"
        save_positions(positions, positions_dir)
        position_rebuilt = True

    # Step 3: Log activity
    activity_logged = False
    if activity_log is not None:
        actor = decision.created_by.value if hasattr(decision, 'created_by') else "human"
        activity_log.append(
            activity_type=ActivityType.DECISION_RECORDED.value,
            obj_id=decision.id,
            actor=actor,
            summary=f"记录{action} {decision.ticker} 决策",
        )
        activity_logged = True

    return DecisionRecord(
        decision=decision,
        position_rebuilt=position_rebuilt,
        activity_logged=activity_logged,
    )
