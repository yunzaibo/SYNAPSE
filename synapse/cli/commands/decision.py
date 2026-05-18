"""CLI command: synapse decision record --symbol --type --thesis

Record a buy/sell decision.
"""

from __future__ import annotations

import argparse

from synapse.core.schemas.decision import Decision, DecisionType
from synapse.core.workflow.decision_flow import record_decision
from synapse.core.naming import generate_id


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the decision subcommand."""
    parser = subparsers.add_parser(
        "decision",
        help="Decision workflows",
        description="Record and manage buy/sell decisions.",
    )
    decision_sub = parser.add_subparsers(dest="decision_command", help="Decision commands")

    # record subcommand
    record_parser = decision_sub.add_parser(
        "record",
        help="Record a buy/sell decision",
        description="Record a buy or sell decision with thesis and risk.",
    )
    record_parser.add_argument(
        "--symbol",
        required=True,
        help="Security symbol (e.g. 600519)",
    )
    record_parser.add_argument(
        "--type",
        required=True,
        choices=["buy", "sell"],
        help="Decision type",
    )
    record_parser.add_argument(
        "--thesis",
        required=True,
        help="Investment thesis",
    )
    record_parser.set_defaults(func=run_record)


def run_record(args: argparse.Namespace) -> int:
    """Execute the decision record command."""
    decision_type = DecisionType(args.type)
    decision_id = generate_id("dec")

    decision = Decision(
        id=decision_id,
        symbol=args.symbol,
        ticker=args.symbol,
        decision_type=decision_type,
        thesis=args.thesis,
    )

    result = record_decision(
        decision=decision,
        existing_decisions=[],
    )

    print(f"Recorded {args.type} decision for {args.symbol}:")
    print(f"  ID: {decision_id}")
    print(f"  Thesis: {args.thesis}")
    print(f"  Position rebuilt: {result.position_rebuilt}")

    return 0
