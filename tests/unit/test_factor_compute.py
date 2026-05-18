import pandas as pd

from synapse.factor.spec import FactorSpec
from synapse.factor.compute import compute_factor


DATA_PATH = "data/sample/sample_prices.csv"


def _load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH, parse_dates=["date"])


def test_compute_momentum():
    data = _load_data()
    spec = FactorSpec(
        factor_id="momentum-20d",
        name="20-Day Momentum",
        description="Price momentum over the last 20 trading days",
        domain="cross_sectional_equity",
        inputs=["close"],
        formula="close / close.shift(20) - 1",
        frequency="daily",
        direction="positive",
        universe="sample-equity",
        created_by="human",
    )
    result = compute_factor(spec, data)
    assert isinstance(result, pd.Series)
    assert len(result) > 0, "Momentum result should not be empty"
    assert not result.isna().all(), "Result should have non-NaN values"


def test_compute_simple_formula():
    data = _load_data()
    spec = FactorSpec(
        factor_id="vol-ratio",
        name="Volume Ratio",
        description="Simple volume field",
        domain="cross_sectional_equity",
        inputs=["volume"],
        formula="volume",
        frequency="daily",
        direction="unknown",
        universe="sample",
        created_by="human",
    )
    result = compute_factor(spec, data)
    assert len(result) > 0
