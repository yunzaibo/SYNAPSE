from pathlib import Path

import pandas as pd

from synapse.data.metadata import DatasetMetadata


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV file into a DataFrame."""
    return pd.read_csv(path)


def load_parquet(path: str | Path) -> pd.DataFrame:
    """Load a Parquet file into a DataFrame."""
    return pd.read_parquet(path)


def load_dataset(
    data_path: str | Path,
    metadata_path: str | Path,
) -> tuple[pd.DataFrame, DatasetMetadata]:
    """Load a dataset and its metadata from disk.

    Returns
    -------
    tuple[pd.DataFrame, DatasetMetadata]
        The data and its time-aware metadata.
    """
    data_path = Path(data_path)
    meta = DatasetMetadata.from_yaml(metadata_path)

    if data_path.suffix == ".csv":
        df = load_csv(data_path)
    elif data_path.suffix == ".parquet":
        df = load_parquet(data_path)
    else:
        raise ValueError(f"Unsupported file format: {data_path.suffix}")

    return df, meta
