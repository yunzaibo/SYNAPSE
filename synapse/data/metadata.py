from dataclasses import dataclass, asdict
from pathlib import Path

import yaml


@dataclass
class DatasetMetadata:
    """Time-aware metadata describing a dataset's lineage and availability."""

    dataset_id: str
    name: str
    source: str
    asset_class: str  # equity | futures | crypto | other
    frequency: str  # daily | intraday | tick | other
    start_date: str
    end_date: str
    timezone: str
    available_at_policy: str
    adjustment_policy: str
    survivorship_policy: str
    missing_value_policy: str
    created_at: str

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DatasetMetadata":
        """Load metadata from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        """Serialize metadata to a YAML file."""
        with open(path, "w") as f:
            yaml.dump(asdict(self), f, default_flow_style=False)
