# Task: IMPL-008 Event CLI Subcommands + Integration Tests

## Implementation Summary

### Files Modified
- `synapse/cli/main.py`: Added `event` import and `event.register(subparsers)` call

### Files Created
- `synapse/cli/commands/event.py`: Event CLI command group with 4 subcommands
- `tests/integration/test_event_pipeline.py`: End-to-end integration test

### Files Modified (Tests)
- `tests/unit/test_cli.py`: Appended `TestEventCLI` class with 6 test methods

## Content Added

### event.py (`synapse/cli/commands/event.py`)
- **register()**: Registers `event` subcommand with 4 sub-parsers: detect, impact, graph, list
- **run_detect(args)**: Loads YAML data, runs all 6 detectors via DetectorRegistry, applies --type and --min-confidence filters
- **run_impact(args)**: Finds event by --event-id, builds PropagationGraph, runs ImpactAnalyzer, outputs text or JSON
- **run_graph(args)**: Builds PropagationGraph, shows nodes/roots/topological sort, optional position-id BFS downstream
- **run_list(args)**: Loads events with filters on --type, --state, --from-date, --to-date
- **_load_events(data_dir)**: Helper to load Event YAML files (id prefix: evt_)

### CLI Arguments
| Subcommand  | Arguments |
|-------------|-----------|
| detect      | --data-dir (required), --type, --min-confidence |
| impact      | --event-id (required), --data-dir (required), --depth, --format |
| graph       | --data-dir (required), --position-id, --direction, --max-depth |
| list        | --data-dir (required), --type, --state, --from-date, --to-date |

### TestEventCLI (6 tests)
- test_event_help: `synapse event --help` returns 0 with "Event" in output
- test_event_detect_args: detect --help shows --data-dir, --type, --min-confidence
- test_event_impact_args: impact --help shows --event-id, --depth, --format
- test_event_graph_args: graph --help shows --direction, --max-depth
- test_event_list_args: list --help shows --state, --from-date, --to-date
- test_event_help_text: All 4 subcommands generate help without error

### test_event_pipeline (1 integration test)
- Creates earnings + policy raw data matching detector triggers
- Detects events via DetectorRegistry (EarningsDetector + PolicyDetector)
- Validates DeduplicationEngine key generation (different sources produce different keys)
- Builds PropagationGraph with 5 nodes, verifies node count
- Runs ImpactAnalyzer, asserts event_id match and total_impact > 0

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.cli.commands.event import register, run_detect, run_impact, run_graph, run_list
```

### Integration Points
- **CLI registration**: `event.register(subparsers)` in `synapse/cli/main.py:29`
- **Command usage**: `synapse event detect --data-dir ./data`
- **Handler return**: All handlers return `int` (0 = success)

## Status: Complete
