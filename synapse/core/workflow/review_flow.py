"""Review Flow — Submit decision post-mortem reviews.

ADR-010: Logs review.completed to activity.jsonl.

Flow:
1. Validate review data
2. Save review to YAML
3. Log activity
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from synapse.core.activity import ActivityLog, ActivityType
from synapse.core.loader import save_object
from synapse.core.schemas.review import Review


@dataclass
class ReviewRecord:
    """Result of submitting a review."""

    review: Review
    saved: bool = False
    activity_logged: bool = False


def submit_review(
    review: Review,
    activity_log: Optional[ActivityLog] = None,
    workspace_dir: Optional[str | Path] = None,
) -> ReviewRecord:
    """Submit a decision review.

    Steps:
    1. Save review to YAML file
    2. Log review.completed activity

    Args:
        review: The review to submit.
        activity_log: ActivityLog to write to. If None, activity is not logged.
        workspace_dir: Workspace root directory. If None, file save is skipped.

    Returns:
        ReviewRecord with the review and save status.
    """
    # Step 1: Save review to YAML if workspace provided
    saved = False
    if workspace_dir is not None:
        workspace = Path(workspace_dir)
        decisions_dir = workspace / "decisions"

        # Review is stored alongside its linked decision
        if review.linked_decision_id:
            # Find the decision directory
            review_path = decisions_dir / review.linked_decision_id / "review.yaml"
            save_object(review, review_path)
            saved = True

    # Step 2: Log activity
    activity_logged = False
    if activity_log is not None:
        actor = review.created_by.value if hasattr(review, 'created_by') else "human"
        activity_log.append(
            activity_type=ActivityType.REVIEW_COMPLETED.value,
            obj_id=review.id,
            actor=actor,
            summary=f"完成决策回顾 {review.linked_decision_id or 'unknown'}",
        )
        activity_logged = True

    return ReviewRecord(
        review=review,
        saved=saved,
        activity_logged=activity_logged,
    )
