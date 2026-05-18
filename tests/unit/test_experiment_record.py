import pytest
import tempfile
from pathlib import Path

from synapse.experiment.record import (
    ExperimentRecord,
    ExperimentStatus,
    ResearchTask,
    TaskState,
    ALLOWED_TRANSITIONS,
)


class TestExperimentRecord:
    def test_create_experiment_record(self):
        record = ExperimentRecord(
            experiment_id="exp-001",
            name="test-experiment",
            research_task_id="task-001",
            data_version="v1.0",
            factor_version="v2.0",
            model_version="v3.0",
            split_method="time-based",
            parameters={"lookback": 60},
            status="draft",
        )
        assert record.experiment_id == "exp-001"
        assert record.name == "test-experiment"
        assert record.status == "draft"
        assert record.parameters == {"lookback": 60}
        assert record.created_by == "human"

    def test_experiment_status_enum(self):
        assert ExperimentStatus.DRAFT == "draft"
        assert ExperimentStatus.RUNNING == "running"
        assert ExperimentStatus.SUCCEEDED == "succeeded"
        assert ExperimentStatus.FAILED == "failed"

    def test_yaml_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "exp.yaml"
            record = ExperimentRecord(
                experiment_id="exp-002",
                name="yaml-roundtrip",
                research_task_id="task-002",
                data_version="v1.0",
                factor_version="v2.0",
                model_version="v3.0",
                split_method="random",
                parameters={"alpha": 0.05},
                status="running",
                created_by="ai",
            )
            record.to_yaml(path)

            loaded = ExperimentRecord.from_yaml(path)
            assert loaded.experiment_id == "exp-002"
            assert loaded.name == "yaml-roundtrip"
            assert loaded.status == "running"
            assert loaded.parameters == {"alpha": 0.05}
            assert loaded.created_by == "ai"


class TestResearchTask:
    def test_create_research_task(self):
        task = ResearchTask(
            task_id="task-001",
            name="test-task",
        )
        assert task.task_id == "task-001"
        assert task.state == "draft"
        assert task.experiment_ids == []

    def test_valid_transition(self):
        task = ResearchTask(task_id="t1", name="trans-test", state="draft")
        assert task.validate_transition("planned") is True

    def test_invalid_transition(self):
        task = ResearchTask(task_id="t1", name="trans-test", state="draft")
        assert task.validate_transition("backtested") is False

    def test_transition_updates_state(self):
        task = ResearchTask(task_id="t1", name="trans-test", state="draft")
        task.transition("planned")
        assert task.state == "planned"
        assert task.updated_at != ""

    def test_transition_raises_on_invalid(self):
        task = ResearchTask(task_id="t1", name="trans-test", state="draft")
        with pytest.raises(ValueError, match="Invalid transition"):
            task.transition("archived")

    def test_full_state_machine_path(self):
        states = [
            "planned",
            "data_ready",
            "factor_defined",
            "audited",
            "backtested",
            "risk_reviewed",
            "reported",
            "archived",
        ]
        task = ResearchTask(task_id="t1", name="full-path", state="draft")
        for s in states:
            task.transition(s)
        assert task.state == "archived"

    def test_cannot_transition_from_archived(self):
        task = ResearchTask(task_id="t1", name="archived", state="archived")
        assert task.validate_transition("draft") is False
        with pytest.raises(ValueError):
            task.transition("draft")

    def test_yaml_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "task.yaml"
            task = ResearchTask(
                task_id="task-003",
                name="yaml-task",
                state="planned",
                experiment_ids=["exp-001", "exp-002"],
            )
            task.to_yaml(path)

            loaded = ResearchTask.from_yaml(path)
            assert loaded.task_id == "task-003"
            assert loaded.state == "planned"
            assert loaded.experiment_ids == ["exp-001", "exp-002"]

    def test_all_allowed_transitions(self):
        """Verify the transition table is complete and correct."""
        for current, targets in ALLOWED_TRANSITIONS.items():
            for target in targets:
                task = ResearchTask(task_id="t", name="check", state=current.value)
                task.transition(target.value)
                assert task.state == target.value
