import pytest

from synapse.data.metadata import DatasetMetadata
from synapse.data.validator import validate_metadata


@pytest.fixture
def valid_metadata():
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


class TestValidateMetadata:
    def test_valid_metadata_passes(self, valid_metadata):
        errors = validate_metadata(valid_metadata)
        assert errors == []

    def test_missing_dataset_id(self, valid_metadata):
        valid_metadata.dataset_id = ""
        errors = validate_metadata(valid_metadata)
        assert any("dataset_id" in e for e in errors)

    def test_missing_timezone(self, valid_metadata):
        valid_metadata.timezone = ""
        errors = validate_metadata(valid_metadata)
        assert any("timezone" in e for e in errors)

    def test_invalid_date_range(self, valid_metadata):
        valid_metadata.start_date = "2024-12-31"
        valid_metadata.end_date = "2024-01-01"
        errors = validate_metadata(valid_metadata)
        assert any("start_date must be before end_date" in e for e in errors)

    def test_multiple_missing_fields(self):
        metadata = DatasetMetadata(
            dataset_id="",
            name="",
            source="",
            asset_class="",
            frequency="",
            start_date="2024-01-01",
            end_date="2024-12-31",
            timezone="UTC",
            available_at_policy="eod",
            adjustment_policy="none",
            survivorship_policy="none",
            missing_value_policy="drop",
            created_at="2024-01-01",
        )
        errors = validate_metadata(metadata)
        assert len(errors) >= 5
