import pytest
import tempfile
import time
from pathlib import Path

from synapse.experiment.tracker import ExperimentTracker
from synapse.experiment.record import ExperimentRecord
from synapse.core.errors import EXPERIMENT_RECORD_MISSING, AGENT_ACTION_NOT_ALLOWED


class TestExperimentTracker:
    def test_create_experiment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExperimentTracker(tmpdir)
            record = tracker.create_experiment(
                name="my-test",
                data_version="v1.0",
                factor_version="v2.0",
                parameters={"lookback": 30},
            )
            assert record.name == "my-test"
            assert record.status == "draft"
            assert record.data_version == "v1.0"
            # File should exist on disk
            path = Path(tmpdir) / f"{record.experiment_id}.yaml"
            assert path.exists()

    def test_update_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExperimentTracker(tmpdir)
            record = tracker.create_experiment(
                name="status-test",
                data_version="v1.0",
                factor_version="v2.0",
                parameters={},
            )
            updated = tracker.update_status(record.experiment_id, "running")
            assert updated.status == "running"

            # Verify file reflects update
            loaded = ExperimentRecord.from_yaml(
                Path(tmpdir) / f"{record.experiment_id}.yaml"
            )
            assert loaded.status == "running"

    def test_update_status_sets_completed_at(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExperimentTracker(tmpdir)
            record = tracker.create_experiment(
                name="completed-test",
                data_version="v1.0",
                factor_version="v2.0",
                parameters={},
            )
            updated = tracker.update_status(record.experiment_id, "succeeded")
            assert updated.completed_at != ""

    def test_update_status_missing_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExperimentTracker(tmpdir)
            with pytest.raises(EXPERIMENT_RECORD_MISSING):
                tracker.update_status("exp-nonexistent", "running")

    def test_list_experiments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExperimentTracker(tmpdir)
            tracker.create_experiment("a", "v1", "v1", {})
            time.sleep(1.1)  # ensure unique timestamp-based IDs
            tracker.create_experiment("b", "v1", "v1", {})
            time.sleep(1.1)
            tracker.create_experiment("c", "v1", "v1", {})
            records = tracker.list_experiments()
            assert len(records) == 3

    def test_list_experiments_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExperimentTracker(tmpdir)
            records = tracker.list_experiments()
            assert records == []

    def test_delete_experiment_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExperimentTracker(tmpdir)
            record = tracker.create_experiment(
                name="delete-test",
                data_version="v1",
                factor_version="v1",
                parameters={},
            )
            with pytest.raises(AGENT_ACTION_NOT_ALLOWED):
                tracker.delete_experiment(record.experiment_id)

    def test_delete_experiment_file_still_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExperimentTracker(tmpdir)
            record = tracker.create_experiment(
                name="still-here",
                data_version="v1",
                factor_version="v1",
                parameters={},
            )
            path = Path(tmpdir) / f"{record.experiment_id}.yaml"
            assert path.exists()

            with pytest.raises(AGENT_ACTION_NOT_ALLOWED):
                tracker.delete_experiment(record.experiment_id)

            # File must still exist after failed delete
            assert path.exists()

    def test_tracker_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "experiments" / "2026"
            tracker = ExperimentTracker(nested)
            assert nested.exists()
            record = tracker.create_experiment(
                name="nested", data_version="v1", factor_version="v1", parameters={}
            )
            assert (nested / f"{record.experiment_id}.yaml").exists()
