# Data Contract

## Purpose

Define minimum metadata for datasets used in SYNAPSE.

## P0 Implemented: DatasetMetadata

```python
@dataclass
class DatasetMetadata:
    dataset_id: str
    name: str
    source: str
    asset_class: str        # equity | futures | crypto | other
    frequency: str          # daily | intraday | tick | other
    start_date: str
    end_date: str
    timezone: str
    available_at_policy: str
    adjustment_policy: str
    survivorship_policy: str
    missing_value_policy: str
    created_at: str
```

Source: `synapse/data/metadata.py`

## Required Concepts

### as_of_date

The research date or evaluation date.

### available_at

The timestamp when the data would have been available to the researcher.

### revision_timestamp

The timestamp when the current stored data version was created or revised.

## P0 Implementation

- `DatasetMetadata` dataclass with YAML serialization (`from_yaml()`, `to_yaml()`)
- `load_dataset(data_path, metadata_path)` returns `(DataFrame, DatasetMetadata)`
- `validate_metadata()` checks required fields and date range consistency
- All metadata fields are explicit — no silent defaults

## API

```python
from synapse.data.loader import load_dataset
from synapse.data.validator import validate_metadata
from synapse.data.metadata import DatasetMetadata

df, meta = load_dataset("data/sample.csv", "data/sample.yaml")
errors = validate_metadata(meta)
```
