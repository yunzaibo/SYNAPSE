import numpy as np
import pandas as pd

from synapse.factor.decay import (
    categorize_decay,
    compute_decay_half_life,
    compute_ic_decay,
)


# ---------------------------------------------------------------------------
# compute_ic_decay tests
# ---------------------------------------------------------------------------

def test_ic_decay_returns_series_with_correct_index():
    """compute_ic_decay should return a Series indexed 0..max_lag."""
    rng = np.random.default_rng(42)
    n = 200
    fv = pd.Series(rng.standard_normal(n))
    fr = pd.Series(rng.standard_normal(n))
    result = compute_ic_decay(fv, fr, max_lag=10)
    assert isinstance(result, pd.Series)
    assert list(result.index) == list(range(11))
    assert result.name == "ic_decay"


def test_ic_decay_lag0_highest_for_decaying_signal():
    """A decaying signal should have the highest IC at lag 0."""
    rng = np.random.default_rng(7)
    n = 300
    # Factor that perfectly predicts next-period return, then decays
    factor = pd.Series(rng.standard_normal(n))
    returns = factor * 0.5 + rng.standard_normal(n) * 0.1
    result = compute_ic_decay(factor, returns, max_lag=20)
    # lag=0 IC should be the highest (absolute value)
    assert abs(result.iloc[0]) >= abs(result.iloc[5])
    assert abs(result.iloc[0]) >= abs(result.iloc[10])


def test_ic_decay_known_perfect_correlation():
    """Perfectly correlated series at lag 0 should have IC ~1.0."""
    n = 100
    fv = pd.Series(range(n), dtype=float)
    fr = pd.Series(range(n), dtype=float)
    result = compute_ic_decay(fv, fr, max_lag=5)
    assert abs(result.iloc[0] - 1.0) < 1e-6


def test_ic_decay_dataframe_input():
    """DataFrame inputs should compute per-column IC and return the mean."""
    rng = np.random.default_rng(99)
    n = 200
    fv = pd.DataFrame({"a": rng.standard_normal(n), "b": rng.standard_normal(n)})
    fr = pd.DataFrame({"a": rng.standard_normal(n), "b": rng.standard_normal(n)})
    result = compute_ic_decay(fv, fr, max_lag=5)
    assert len(result) == 6
    assert result.dtype == float


def test_ic_decay_max_lag_zero():
    """max_lag=0 should return a single-element Series."""
    rng = np.random.default_rng(1)
    fv = pd.Series(rng.standard_normal(50))
    fr = pd.Series(rng.standard_normal(50))
    result = compute_ic_decay(fv, fr, max_lag=0)
    assert len(result) == 1
    assert 0 in result.index


# ---------------------------------------------------------------------------
# compute_decay_half_life tests
# ---------------------------------------------------------------------------

def test_half_life_fast_decay():
    """IC that drops below half within 3 lags should give half-life = 3."""
    ic_decay = pd.Series([0.8, 0.6, 0.4, 0.3, 0.2, 0.1], index=range(6))
    assert compute_decay_half_life(ic_decay) == 3


def test_half_life_never_decays():
    """If IC never drops below half, returns the max lag."""
    ic_decay = pd.Series([0.8, 0.7, 0.6, 0.5, 0.45, 0.41], index=range(6))
    assert compute_decay_half_life(ic_decay) == 5


def test_half_life_immediate_decay():
    """IC drops below half at lag 1."""
    ic_decay = pd.Series([0.8, 0.3, 0.2, 0.1], index=range(4))
    assert compute_decay_half_life(ic_decay) == 1


def test_half_life_empty_series():
    """Empty series should return 0."""
    ic_decay = pd.Series(dtype=float)
    assert compute_decay_half_life(ic_decay) == 0


def test_half_life_zero_peak():
    """Zero peak IC should return 0."""
    ic_decay = pd.Series([0.0, 0.0, 0.0], index=range(3))
    assert compute_decay_half_life(ic_decay) == 0


def test_half_life_nan_peak():
    """NaN peak IC should return 0."""
    ic_decay = pd.Series([float("nan"), 0.1, 0.05], index=range(3))
    assert compute_decay_half_life(ic_decay) == 0


# ---------------------------------------------------------------------------
# categorize_decay tests
# ---------------------------------------------------------------------------

def test_categorize_fast_decay():
    assert categorize_decay(0) == "fast_decay"
    assert categorize_decay(4) == "fast_decay"


def test_categorize_medium_decay():
    assert categorize_decay(5) == "medium_decay"
    assert categorize_decay(19) == "medium_decay"


def test_categorize_slow_decay():
    assert categorize_decay(20) == "slow_decay"
    assert categorize_decay(59) == "slow_decay"


def test_categorize_very_slow_decay():
    assert categorize_decay(60) == "very_slow_decay"
    assert categorize_decay(120) == "very_slow_decay"


def test_categorize_boundary_values():
    """Check the exact boundary transitions."""
    assert categorize_decay(4) == "fast_decay"
    assert categorize_decay(5) == "medium_decay"
    assert categorize_decay(19) == "medium_decay"
    assert categorize_decay(20) == "slow_decay"
    assert categorize_decay(59) == "slow_decay"
    assert categorize_decay(60) == "very_slow_decay"
