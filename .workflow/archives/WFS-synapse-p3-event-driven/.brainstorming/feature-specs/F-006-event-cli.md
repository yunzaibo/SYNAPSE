# F-006: Event CLI Subcommands

## Component #13: CLI Integration

### Overview
Three new CLI subcommands under `synapse event` group for event detection, impact analysis, and propagation graph inspection.

### Commands

#### `synapse event detect --data-dir PATH`
- Run all registered detectors against data directory
- Output: list of detected events with confidence scores
- Flags: `--type` (filter by event type), `--min-confidence` (threshold)

#### `synapse event impact --event-id ID`
- Compute impact report for a specific event
- Output: direct/cascaded/aggregate impacts
- Flags: `--depth` (max propagation depth), `--format` (text/json)

#### `synapse event graph --position-id ID`
- Show propagation graph for a position
- Output: upstream events, downstream effects, graph metrics
- Flags: `--direction` (upstream/downstream/both), `--max-depth`

#### `synapse event list --data-dir PATH`
- List all events with filtering
- Flags: `--type`, `--state`, `--from-date`, `--to-date`

### Implementation Pattern
```python
def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("event", help="Event commands")
    event_sub = parser.add_subparsers(dest="event_cmd")
    # detect, impact, graph, list subparsers
```

### Tests (~8 tests)
- `event detect` subcommand registration
- `event detect` argument parsing
- `event impact` subcommand registration
- `event impact` argument parsing
- `event graph` subcommand registration
- `event graph` argument parsing
- `event list` subcommand registration
- Full CLI help text generation
