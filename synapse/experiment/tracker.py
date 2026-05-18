from pathlib import Path
from datetime import datetime

from synapse.experiment.record import ExperimentRecord
from synapse.core.errors import EXPERIMENT_RECORD_MISSING, AGENT_ACTION_NOT_ALLOWED


class ExperimentTracker:
    def __init__(self, experiment_dir: str | Path):
        self.experiment_dir = Path(experiment_dir)
        self.experiment_dir.mkdir(parents=True, exist_ok=True)

    def create_experiment(
        self,
        name: str,
        data_version: str,
        factor_version: str,
        parameters: dict,
        created_by: str = "human",
    ) -> ExperimentRecord:
        experiment_id = f"exp-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        record = ExperimentRecord(
            experiment_id=experiment_id,
            name=name,
            research_task_id="",
            data_version=data_version,
            factor_version=factor_version,
            model_version="",
            split_method="",
            parameters=parameters,
            started_at=datetime.now().isoformat(),
            status="draft",
            created_by=created_by,
        )
        record.to_yaml(self.experiment_dir / f"{experiment_id}.yaml")
        return record

    def update_status(
        self,
        experiment_id: str,
        new_status: str,
        triggered_by: str = "human",
    ) -> ExperimentRecord:
        path = self.experiment_dir / f"{experiment_id}.yaml"
        if not path.exists():
            raise EXPERIMENT_RECORD_MISSING(f"Experiment {experiment_id} not found")

        record = ExperimentRecord.from_yaml(path)
        record.status = new_status
        if new_status in ("succeeded", "failed"):
            record.completed_at = datetime.now().isoformat()
        record.to_yaml(path)
        return record

    def list_experiments(self) -> list[ExperimentRecord]:
        records = []
        for p in sorted(self.experiment_dir.glob("*.yaml")):
            records.append(ExperimentRecord.from_yaml(p))
        return records

    def delete_experiment(self, experiment_id: str) -> None:
        """Governance: experiments cannot be deleted."""
        raise AGENT_ACTION_NOT_ALLOWED(
            f"Experiment {experiment_id} cannot be deleted — governance policy"
        )
