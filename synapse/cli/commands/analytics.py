"""CLI command: synapse analytics error-pattern / behavioral

Run analytics subcommands against local research data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from synapse.core.schemas.review import Review, SignalEvaluation
from synapse.core.schemas.decision import Decision, AttentionOrigin, TimeHorizon
from synapse.core.schemas.position import Position
from synapse.core.schemas.event import Event
from synapse.analytics.error_pattern import ErrorPatternAnalyzer
from synapse.analytics.behavioral import BehavioralStatsAnalyzer
from synapse.analytics.correlation import CorrelationAnalyzer
from synapse.analytics.drift import DriftDetector


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the analytics subcommand."""
    parser = subparsers.add_parser(
        "analytics",
        help="Analytics commands",
        description="Run analytics on research data.",
    )
    analytics_sub = parser.add_subparsers(
        dest="analytics_command", help="Analytics commands"
    )

    # error-pattern subcommand
    ep_parser = analytics_sub.add_parser(
        "error-pattern",
        help="Analyze signal accuracy across reviews",
        description="Load Reviews from a directory and analyze signal accuracy patterns.",
    )
    ep_parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing Review YAML files",
    )
    ep_parser.set_defaults(func=run_error_pattern)

    # behavioral subcommand
    beh_parser = analytics_sub.add_parser(
        "behavioral",
        help="Analyze decision behavioral statistics",
        description="Load Decisions from a directory and compute behavioral stats.",
    )
    beh_parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing Decision YAML files",
    )
    beh_parser.set_defaults(func=run_behavioral)

    # correlation subcommand
    corr_parser = analytics_sub.add_parser(
        "correlation",
        help="Analyze event-to-review correlation",
        description="Load Events and Reviews from a directory and analyze correlation.",
    )
    corr_parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing Event and Review YAML files",
    )
    corr_parser.set_defaults(func=run_correlation)

    # drift subcommand
    drift_parser = analytics_sub.add_parser(
        "drift",
        help="Analyze thesis drift via position state transitions",
        description="Load Positions, Theses, and Reviews from a directory and detect drift.",
    )
    drift_parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing Position, Thesis, and Review YAML files",
    )
    drift_parser.set_defaults(func=run_drift)


def _load_yaml_objects(data_dir: Path, id_prefix: str) -> list[dict]:
    """Load all YAML files from data_dir that have matching id prefix."""
    objects = []
    if not data_dir.is_dir():
        return objects
    for yml_file in sorted(data_dir.glob("*.yaml")):
        try:
            with open(yml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict) and data.get("id", "").startswith(id_prefix):
                objects.append(data)
        except Exception:
            continue
    return objects


def run_error_pattern(args: argparse.Namespace) -> int:
    """Execute the error-pattern analytics command."""
    data_dir = Path(args.data_dir)
    raw_objects = _load_yaml_objects(data_dir, "rev_")

    reviews = [Review.from_dict(obj) for obj in raw_objects]
    report = ErrorPatternAnalyzer().analyze(reviews)

    print(f"Error Pattern Analysis ({len(reviews)} reviews)")
    print(f"  Overall accuracy: {report.overall_accuracy:.1%}")
    print(f"  Total signals evaluated: {report.total_signals_evaluated}")
    print(f"  Trend: {report.trend.value}")
    if report.worst_performers:
        print(f"  Worst performers: {', '.join(report.worst_performers)}")
    if report.per_signal_type_accuracy:
        print("  Per-signal accuracy:")
        for sig_type, acc in sorted(report.per_signal_type_accuracy.items()):
            print(f"    {sig_type}: {acc:.1%}")

    return 0


def run_behavioral(args: argparse.Namespace) -> int:
    """Execute the behavioral analytics command."""
    data_dir = Path(args.data_dir)
    raw_objects = _load_yaml_objects(data_dir, "dec_")

    decisions = [Decision.from_dict(obj) for obj in raw_objects]
    report = BehavioralStatsAnalyzer().analyze(decisions)

    print(f"Behavioral Statistics ({report.total_decisions} decisions)")
    print(f"  Decision frequency: {report.decision_frequency_per_week:.1f}/week")
    print(f"  Avg signals per decision: {report.avg_signals_per_decision:.1f}")
    print(f"  Period: {report.period_days} days")
    if report.decision_type_distribution:
        print("  Decision type distribution:")
        for dt, pct in report.decision_type_distribution.items():
            print(f"    {dt}: {pct:.1f}%")
    if report.attention_origin_distribution:
        print("  Attention origin distribution:")
        for ao, pct in report.attention_origin_distribution.items():
            print(f"    {ao}: {pct:.1f}%")

    return 0


def run_correlation(args: argparse.Namespace) -> int:
    """Execute the correlation analytics command."""
    data_dir = Path(args.data_dir)

    event_dicts = _load_yaml_objects(data_dir, "evt_")
    review_dicts = _load_yaml_objects(data_dir, "rev_")

    events = [Event.from_dict(obj) for obj in event_dicts]
    reviews = [Review.from_dict(obj) for obj in review_dicts]
    report = CorrelationAnalyzer().analyze(events, reviews)

    print(f"Correlation Analysis ({len(events)} events, {len(reviews)} reviews)")
    print(f"  Event-review pairs: {report.total_event_review_pairs}")
    print(f"  Correlation strength: {report.correlation_strength:.1%}")
    print(f"  Overall calibration: {report.overall_calibration_score:.3f}")
    if report.event_type_success_rate:
        print("  Success rate by event type:")
        for etype, rate in sorted(report.event_type_success_rate.items()):
            print(f"    {etype}: {rate:.1%}")
    if report.unlinked_events:
        print(f"  Unlinked events: {', '.join(report.unlinked_events)}")

    return 0


def run_drift(args: argparse.Namespace) -> int:
    """Execute the drift analytics command."""
    data_dir = Path(args.data_dir)

    pos_dicts = _load_yaml_objects(data_dir, "pos_")
    review_dicts = _load_yaml_objects(data_dir, "rev_")

    positions = [Position.from_dict(obj) for obj in pos_dicts]
    reviews = [Review.from_dict(obj) for obj in review_dicts]
    report = DriftDetector().detect(positions, reviews=reviews)

    print(f"Drift Analysis ({report.total_positions_tracked} positions)")
    print(f"  Health score: {report.health_score:.2f}")
    print(f"  Drift velocity: {report.drift_velocity_per_day:.3f}/day")
    print(f"  Recovery count: {report.recovery_count}")
    if report.weakening_signals:
        print(f"  Weakening signals: {', '.join(report.weakening_signals)}")
    if report.drift_timeline:
        print(f"  Timeline entries: {len(report.drift_timeline)}")

    return 0
