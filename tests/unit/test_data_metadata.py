import os
import tempfile

import pytest

from synapse.data.metadata import DatasetMetadata


@pytest.fixture
def sample_metadata():
    return DatasetMetadata(
        dataset_id="test-ds",
        name="Test Dataset",
        source="unit-test",
        asset_class="equity",
        frequency="daily",
        start_date="2024-01-01",
        end_date="2024-06-30",
        timezone="UTC",
        available_at_policy="end-of-day",
        adjustment_policy="none",
        survivorship_policy="none",
        missing_value_policy="drop",
        created_at="2024-07-01",
    )


class TestDatasetMetadata:
    def test_create_metadata(self, sample_metadata):
        assert sample_metadata.dataset_id == "test-ds"
        assert sample_metadata.asset_class == "equity"
        assert sample_metadata.frequency == "daily"

    def test_to_yaml_and_back(self, sample_metadata):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            path = f.name
        try:
            sample_metadata.to_yaml(path)
            loaded = DatasetMetadata.from_yaml(path)
            assert loaded.dataset_id == sample_metadata.dataset_id
            assert loaded.start_date == sample_metadata.start_date
            assert loaded.timezone == sample_metadata.timezone
        finally:
            os.unlink(path)

    def test_from_yaml_sample_file(self):
        meta = DatasetMetadata.from_yaml("data/sample/sample_prices.yaml")
        assert meta.dataset_id == "sample-prices"
        assert meta.asset_class == "equity"
        assert meta.frequency == "daily"
        assert meta.start_date == "2024-01-01"
        assert meta.end_date == "2024-05-10"

    def test_fields_preserved_through_yaml(self, sample_metadata):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            path = f.name
        try:
            sample_metadata.to_yaml(path)
            loaded = DatasetMetadata.from_yaml(path)
            assert loaded.adjustment_policy == "none"
            assert loaded.survivorship_policy == "none"
            assert loaded.missing_value_policy == "drop"
            assert loaded.created_at == "2024-07-01"
        finally:
            os.unlink(path)
