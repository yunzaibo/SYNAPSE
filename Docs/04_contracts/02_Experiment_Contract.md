# Experiment Contract

## Purpose

Define experiment metadata and governance rules.

## P0 Implemented: ExperimentRecord

```python
@dataclass
class ExperimentRecord:
    experiment_id: str
    name: str
    research_task_id: str
    data_version: str
    factor_version: str
    model_version: str
    split_method: str
    parameters: dict
    started_at: str
    completed_at: str
    status: str             # draft | running | succeeded | failed
    artifacts: list
    created_by: str         # human | ai | mixed
```

Source: `synapse/experiment/record.py`

## P0 Implemented: ResearchTask State Machine

```python
class TaskState(Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    DATA_READY = "data_ready"
    FACTOR_DEFINED = "factor_defined"
    AUDITED = "audited"
    BACKTESTED = "backtested"
    RISK_REVIEWED = "risk_reviewed"
    REPORTED = "reported"
    ARCHIVED = "archived"
```

Linear path: draft → planned → data_ready → factor_defined → audited → backtested → risk_reviewed → reported → archived.

Source: `synapse/experiment/record.py`

## Experiment Rules

- Every run must create a record.
- Failed runs must not be deleted.
- Parameter changes must create a new record.
- Best-result-only reporting is forbidden.
- AI-generated changes must be marked.

## API

```python
from synapse.experiment.tracker import ExperimentTracker

tracker = ExperimentTracker("experiments/")
exp = tracker.create_experiment(name="test", data_version="v1", factor_version="v1", parameters={})
tracker.update_status(exp.experiment_id, "running")
tracker.delete_experiment(exp.experiment_id)  # raises AGENT_ACTION_NOT_ALLOWED
```
