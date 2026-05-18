from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import yaml
from datetime import datetime


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TaskState(str, Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    DATA_READY = "data_ready"
    FACTOR_DEFINED = "factor_defined"
    AUDITED = "audited"
    BACKTESTED = "backtested"
    RISK_REVIEWED = "risk_reviewed"
    REPORTED = "reported"
    ARCHIVED = "archived"


# Allowed state transitions: current -> list of valid targets
ALLOWED_TRANSITIONS = {
    TaskState.DRAFT: [TaskState.PLANNED],
    TaskState.PLANNED: [TaskState.DATA_READY],
    TaskState.DATA_READY: [TaskState.FACTOR_DEFINED],
    TaskState.FACTOR_DEFINED: [TaskState.AUDITED],
    TaskState.AUDITED: [TaskState.BACKTESTED],
    TaskState.BACKTESTED: [TaskState.RISK_REVIEWED],
    TaskState.RISK_REVIEWED: [TaskState.REPORTED],
    TaskState.REPORTED: [TaskState.ARCHIVED],
    TaskState.ARCHIVED: [],
}


@dataclass
class ExperimentRecord:
    experiment_id: str
    name: str
    research_task_id: str
    data_version: str
    factor_version: str
    model_version: str
    split_method: str
    parameters: dict = field(default_factory=dict)
    started_at: str = ""
    completed_at: str = ""
    status: str = "draft"
    artifacts: list = field(default_factory=list)
    created_by: str = "human"  # human | ai | mixed

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ExperimentRecord":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        with open(path, "w") as f:
            yaml.dump(asdict(self), f, default_flow_style=False)


@dataclass
class ResearchTask:
    task_id: str
    name: str
    state: str = "draft"
    experiment_ids: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def validate_transition(self, new_state: str) -> bool:
        current = TaskState(self.state)
        target = TaskState(new_state)
        return target in ALLOWED_TRANSITIONS.get(current, [])

    def transition(self, new_state: str) -> None:
        if not self.validate_transition(new_state):
            raise ValueError(f"Invalid transition: {self.state} -> {new_state}")
        self.state = new_state
        self.updated_at = datetime.now().isoformat()

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ResearchTask":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        with open(path, "w") as f:
            yaml.dump(asdict(self), f, default_flow_style=False)
