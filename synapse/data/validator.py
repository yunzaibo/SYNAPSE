from synapse.data.metadata import DatasetMetadata

REQUIRED_FIELDS = [
    "dataset_id",
    "name",
    "source",
    "asset_class",
    "frequency",
    "start_date",
    "end_date",
    "timezone",
]


def validate_metadata(metadata: DatasetMetadata) -> list[str]:
    """Validate dataset metadata. Returns a list of error messages (empty = valid)."""
    errors = []

    for field_name in REQUIRED_FIELDS:
        value = getattr(metadata, field_name, None)
        if not value:
            errors.append(f"{field_name} is missing or empty")

    if metadata.start_date and metadata.end_date:
        if metadata.start_date > metadata.end_date:
            errors.append("start_date must be before end_date")

    return errors
