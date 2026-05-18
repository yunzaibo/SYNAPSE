"""CLI command: synapse review submit --decision-id --outcome

Submit a decision post-mortem review.
"""

from __future__ import annotations

import argparse

from synapse.core.schemas.review import Review, ReviewOutcome
from synapse.core.workflow.review_flow import submit_review
from synapse.core.naming import generate_id


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the review subcommand."""
    parser = subparsers.add_parser(
        "review",
        help="Review workflows",
        description="Submit decision post-mortem reviews.",
    )
    review_sub = parser.add_subparsers(dest="review_command", help="Review commands")

    # submit subcommand
    submit_parser = review_sub.add_parser(
        "submit",
        help="Submit a decision review",
        description="Submit a post-mortem review for a recorded decision.",
    )
    submit_parser.add_argument(
        "--decision-id",
        required=True,
        help="ID of the decision to review",
    )
    submit_parser.add_argument(
        "--outcome",
        required=True,
        choices=["thesis_confirmed", "partially_confirmed", "thesis_invalidated"],
        help="Review outcome",
    )
    submit_parser.set_defaults(func=run_submit)


def run_submit(args: argparse.Namespace) -> int:
    """Execute the review submit command."""
    review_outcome = ReviewOutcome(args.outcome)
    review_id = generate_id("rev")

    review = Review(
        id=review_id,
        linked_decision_id=args.decision_id,
        review_outcome=review_outcome,
    )

    result = submit_review(
        review=review,
    )

    print(f"Submitted review for {args.decision_id}:")
    print(f"  Review ID: {review_id}")
    print(f"  Outcome: {args.outcome}")
    print(f"  Saved: {result.saved}")

    return 0
