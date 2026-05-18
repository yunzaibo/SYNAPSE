"""CLI command: synapse event detect / impact / graph / list

Run event-related commands against local research data.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

from synapse.core.schemas.event import Event
from synapse.event.detectors import (
    CapitalFlowDetector,
    CorporateActionDetector,
    EarningsDetector,
    PolicyDetector,
    SentimentDetector,
    ThemeDetector,
)
from synapse.event.graph import PropagationGraph
from synapse.event.impact import ImpactAnalyzer
from synapse.event.registry import DetectorRegistry


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the event subcommand."""
    parser = subparsers.add_parser(
        "event",
        help="Event detection and impact analysis",
        description="Event detection, impact analysis, and propagation graph commands.",
    )
    event_sub = parser.add_subparsers(
        dest="event_command", help="Event commands"
    )

    # detect subcommand
    detect_parser = event_sub.add_parser(
        "detect",
        help="Run event detectors on data directory",
        description="Run all registered detectors against data files.",
    )
    detect_parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing data YAML files",
    )
    detect_parser.add_argument(
        "--type",
        default=None,
        help="Filter by event type (earnings, policy, etc.)",
    )
    detect_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum confidence threshold (0.0-1.0)",
    )
    detect_parser.set_defaults(func=run_detect)

    # impact subcommand
    impact_parser = event_sub.add_parser(
        "impact",
        help="Compute impact report for an event",
        description="Analyze event impact through propagation graph.",
    )
    impact_parser.add_argument(
        "--event-id",
        required=True,
        help="Event ID to analyze",
    )
    impact_parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing event/thesis/position YAML files",
    )
    impact_parser.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Max propagation depth (default: 5)",
    )
    impact_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    impact_parser.set_defaults(func=run_impact)

    # graph subcommand
    graph_parser = event_sub.add_parser(
        "graph",
        help="Show propagation graph",
        description="Display the event propagation graph structure.",
    )
    graph_parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing event YAML files",
    )
    graph_parser.add_argument(
        "--position-id",
        default=None,
        help="Filter by position ID",
    )
    graph_parser.add_argument(
        "--direction",
        choices=["downstream", "upstream"],
        default="downstream",
        help="Traversal direction",
    )
    graph_parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="Max traversal depth",
    )
    graph_parser.set_defaults(func=run_graph)

    # list subcommand
    list_parser = event_sub.add_parser(
        "list",
        help="List events with filters",
        description="List and filter stored events.",
    )
    list_parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing event YAML files",
    )
    list_parser.add_argument(
        "--type",
        default=None,
        help="Filter by event type",
    )
    list_parser.add_argument(
        "--state",
        default=None,
        help="Filter by propagation state",
    )
    list_parser.add_argument(
        "--from-date",
        default=None,
        help="Start date filter (YYYY-MM-DD)",
    )
    list_parser.add_argument(
        "--to-date",
        default=None,
        help="End date filter (YYYY-MM-DD)",
    )
    list_parser.set_defaults(func=run_list)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _load_events(data_dir: Path) -> list[Event]:
    """Load all Event YAML files from directory."""
    events: list[Event] = []
    if not data_dir.is_dir():
        return events
    for yml_file in sorted(data_dir.glob("*.yaml")):
        try:
            with open(yml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict) and data.get("id", "").startswith("evt_"):
                events.append(Event.from_dict(data))
        except Exception:
            continue
    return events


# ------------------------------------------------------------------
# Handler functions
# ------------------------------------------------------------------


def run_detect(args: argparse.Namespace) -> int:
    """Execute event detection command."""
    data_dir = Path(args.data_dir)

    if not data_dir.is_dir():
        print(f"Error: data directory does not exist: {data_dir}", file=sys.stderr)
        return 1

    # Build registry with all 6 detectors
    registry = DetectorRegistry()
    for cls in [
        EarningsDetector,
        PolicyDetector,
        SentimentDetector,
        ThemeDetector,
        CapitalFlowDetector,
        CorporateActionDetector,
    ]:
        registry.register(cls)

    # Load data files
    raw_objects: list[dict] = []
    for yml_file in sorted(data_dir.glob("*.yaml")):
        try:
            with open(yml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                raw_objects.append(data)
        except Exception:
            continue

    # Run detection
    all_events: list[Event] = []
    for obj in raw_objects:
        events = registry.detect_all(obj)
        all_events.extend(events)

    # Apply filters
    if args.type:
        all_events = [e for e in all_events if e.event_type.value == args.type]
    if args.min_confidence > 0:
        all_events = [
            e for e in all_events if e.confidence >= args.min_confidence
        ]

    print(f"Event Detection ({len(all_events)} events detected)")
    for event in all_events:
        print(
            f"  [{event.event_type.value}] {event.title} "
            f"(confidence: {event.confidence:.2f})"
        )

    return 0


def run_impact(args: argparse.Namespace) -> int:
    """Execute impact analysis command."""
    data_dir = Path(args.data_dir)
    events = _load_events(data_dir)

    # Find target event
    target = next((e for e in events if e.id == args.event_id), None)
    if target is None:
        print(f"Error: Event {args.event_id} not found", file=sys.stderr)
        return 1

    # NOTE: Naive graph model -- this is a simplified placeholder, not a
    # real persistence-backed graph.  Every event of the same type (e.g.
    # two "earnings" events) will share the *same* synthetic thesis node
    # (thesis_earnings), which collapses them onto a single downstream
    # path.  A production implementation should resolve per-event thesis
    # nodes from stored graph data rather than synthesising them here.
    graph = PropagationGraph()
    for event in events:
        graph.add_edge(
            event.id,
            f"thesis_{event.event_type.value}",
            weight=0.5,
        )

    analyzer = ImpactAnalyzer(graph, target, days_since_event=0.0)
    report = analyzer.compute_full_report()

    if args.format == "json":
        import json as json_mod

        print(json_mod.dumps(report.to_dict(), indent=2))
    else:
        print(f"Impact Report for {args.event_id}")
        print(f"  Direct impacts: {len(report.direct_impacts)}")
        print(f"  Cascaded impacts: {len(report.cascaded_impacts)}")
        print(f"  Total impact: {report.total_impact:.4f}")
        print(f"  Max impact entity: {report.max_impact_entity}")

    return 0


def run_graph(args: argparse.Namespace) -> int:
    """Execute graph visualization command."""
    data_dir = Path(args.data_dir)
    events = _load_events(data_dir)

    graph = PropagationGraph()
    for event in events:
        graph.add_edge(
            event.id,
            f"thesis_{event.event_type.value}",
            weight=0.5,
        )

    nodes = graph.get_all_nodes()
    roots = graph.get_roots()

    print(f"Propagation Graph ({len(nodes)} nodes)")
    root_display = ", ".join(roots[:5])
    if len(roots) > 5:
        root_display += "..."
    print(f"  Roots: {root_display}")

    if args.position_id:
        downstream = graph.bfs_downstream(
            args.position_id, max_depth=args.max_depth
        )
        print(
            f"  Downstream from {args.position_id}: "
            f"{len(downstream)} nodes"
        )
    else:
        topo = graph.topological_sort()
        topo_display = ", ".join(topo[:5])
        if len(topo) > 5:
            topo_display += "..."
        print(f"  Topological order: {topo_display}")

    return 0


def run_list(args: argparse.Namespace) -> int:
    """Execute event list command."""
    data_dir = Path(args.data_dir)
    events = _load_events(data_dir)

    # Apply filters
    if args.type:
        events = [e for e in events if e.event_type.value == args.type]
    if args.state:
        events = [
            e for e in events if e.propagation_state.value == args.state
        ]
    if args.from_date:
        from_date = date.fromisoformat(args.from_date)
        events = [
            e for e in events if e.event_date and e.event_date >= from_date
        ]
    if args.to_date:
        to_date = date.fromisoformat(args.to_date)
        events = [
            e for e in events if e.event_date and e.event_date <= to_date
        ]

    print(f"Events ({len(events)} total)")
    for event in events:
        state = event.propagation_state.value
        print(f"  [{event.event_type.value}] {event.title} ({state})")

    return 0
