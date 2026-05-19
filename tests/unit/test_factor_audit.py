import numpy as np
import pandas as pd

from synapse.factor.audit import (
    FactorAuditReport,
    FactorAuditResult,
    audit_factor,
    compute_ic,
    compute_icir,
    compute_rank_ic,
    compute_rolling_ic,
    rate_factor,
)


# ---------------------------------------------------------------------------
# Legacy audit tests (kept as-is)
# ---------------------------------------------------------------------------

def test_audit_returns_floats():
    rng = np.random.default_rng(42)
    n = 100
    fv = pd.Series(rng.standard_normal(n))
    fr = pd.Series(rng.standard_normal(n))
    result = audit_factor(fv, fr, factor_id="test", version="1.0")
    assert isinstance(result, FactorAuditResult)
    assert isinstance(result.ic, float)
    assert isinstance(result.rank_ic, float)


def test_audit_coverage_range():
    rng = np.random.default_rng(42)
    n = 100
    fv = pd.Series(rng.standard_normal(n))
    fr = pd.Series(rng.standard_normal(n))
    result = audit_factor(fv, fr)
    assert 0 <= result.coverage <= 1
    assert 0 <= result.missing_rate <= 1


def test_audit_insufficient_data():
    fv = pd.Series([1.0, 2.0])
    fr = pd.Series([3.0, 4.0])
    result = audit_factor(fv, fr)
    assert result.notes == "Insufficient data for audit"
    assert result.leakage_risk == "unknown"


def test_audit_with_known_correlation():
    n = 50
    x = pd.Series(range(n), dtype=float)
    y = pd.Series(range(n), dtype=float) * 2  # perfectly correlated
    result = audit_factor(x, y)
    assert result.ic > 0.99
    assert result.rank_ic > 0.99
    assert result.leakage_risk == "high"


# ---------------------------------------------------------------------------
# New F-012: compute_ic tests
# ---------------------------------------------------------------------------

def test_compute_ic_perfect_positive():
    """Perfect positive correlation should yield IC ~1.0."""
    x = pd.Series(range(100), dtype=float)
    y = pd.Series(range(100), dtype=float)
    assert compute_ic(x, y) == 1.0


def test_compute_ic_perfect_negative():
    """Perfect negative correlation should yield IC ~-1.0."""
    x = pd.Series(range(100), dtype=float)
    y = pd.Series(range(100, 0, -1), dtype=float)
    assert compute_ic(x, y) == -1.0


def test_compute_ic_no_correlation():
    """Random data should yield IC near 0."""
    rng = np.random.default_rng(99)
    x = pd.Series(rng.standard_normal(200))
    y = pd.Series(rng.standard_normal(200))
    ic = compute_ic(x, y)
    assert abs(ic) < 0.2


def test_compute_ic_with_nan():
    """NaN values should be dropped before computing IC."""
    x = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0])
    y = pd.Series([1.0, 2.0, 3.0, np.nan, 5.0])
    ic = compute_ic(x, y)
    # After dropping NaN rows, 3 valid pairs remain (rows 0,1,4)
    assert isinstance(ic, float)


def test_compute_ic_insufficient_data():
    """Less than 2 valid points should return 0.0."""
    x = pd.Series([1.0])
    y = pd.Series([1.0])
    assert compute_ic(x, y) == 0.0


# ---------------------------------------------------------------------------
# New F-012: compute_rank_ic tests
# ---------------------------------------------------------------------------

def test_compute_rank_ic_monotonic():
    """Perfectly monotonic data should yield RankIC ~1.0."""
    x = pd.Series(range(100), dtype=float)
    y = pd.Series(range(100), dtype=float) ** 2  # monotonic but non-linear
    assert compute_rank_ic(x, y) > 0.99


def test_compute_rank_ic_known_values():
    """Known Spearman value: [1,2,3,4,5] vs [5,6,7,8,9] should be exactly 1.0."""
    x = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    y = pd.Series([5.0, 6.0, 7.0, 8.0, 9.0])
    assert compute_rank_ic(x, y) == 1.0


def test_compute_rank_ic_inverse():
    """Inverse monotonic data should yield RankIC ~-1.0."""
    x = pd.Series(range(50), dtype=float)
    y = pd.Series(range(50, 0, -1), dtype=float)
    assert compute_rank_ic(x, y) < -0.99


def test_compute_rank_ic_insufficient_data():
    """Less than 2 valid points should return 0.0."""
    x = pd.Series([1.0])
    y = pd.Series([2.0])
    assert compute_rank_ic(x, y) == 0.0


# ---------------------------------------------------------------------------
# New F-012: compute_rolling_ic tests
# ---------------------------------------------------------------------------

def test_compute_rolling_ic_window():
    """Rolling IC with known window should produce correct-length output."""
    rng = np.random.default_rng(7)
    n = 120
    df = pd.DataFrame({
        "factor": rng.standard_normal(n),
        "forward_return": rng.standard_normal(n),
    })
    result = compute_rolling_ic(df, window=60)
    assert isinstance(result, pd.Series)
    # First 59 values should be NaN, rest should be floats
    assert len(result) == n
    assert result.iloc[:59].isna().all()
    assert result.iloc[59:].notna().all()


def test_compute_rolling_ic_short_data():
    """Data shorter than window should return empty Series."""
    df = pd.DataFrame({
        "factor": [1.0, 2.0, 3.0],
        "forward_return": [1.0, 2.0, 3.0],
    })
    result = compute_rolling_ic(df, window=60)
    assert len(result) == 0


def test_compute_rolling_ic_drops_nan():
    """Rows with NaN in factor or forward_return should be dropped."""
    df = pd.DataFrame({
        "factor": [1.0, np.nan, 3.0, 4.0, 5.0],
        "forward_return": [1.0, 2.0, 3.0, 4.0, 5.0],
    })
    result = compute_rolling_ic(df, window=3)
    # Row 1 is dropped (NaN factor), so 4 rows remain, window=3 => 2 IC values
    assert result.notna().sum() == 2


# ---------------------------------------------------------------------------
# New F-012: compute_icir tests
# ---------------------------------------------------------------------------

def test_compute_icir_normal():
    """ICIR = mean/std for normal values."""
    assert compute_icir(0.3, 0.1) == 3.0


def test_compute_icir_zero_std():
    """Zero std should return 0.0."""
    assert compute_icir(0.5, 0.0) == 0.0


def test_compute_icir_nan_std():
    """NaN std should return 0.0."""
    assert compute_icir(0.5, float("nan")) == 0.0


# ---------------------------------------------------------------------------
# New F-012: FactorAuditReport creation
# ---------------------------------------------------------------------------

def test_factor_audit_report_creation():
    """FactorAuditReport should hold all F-012 fields."""
    report = FactorAuditReport(
        factor_name="momentum_6m",
        ic_mean=0.05,
        ic_std=0.1,
        icir=0.5,
        rank_ic_mean=0.06,
        turnover=0.3,
        decay_half_life=15,
        coverage=0.85,
        rating="A",
    )
    assert report.factor_name == "momentum_6m"
    assert report.ic_mean == 0.05
    assert report.icir == 0.5
    assert report.rating == "A"
    assert report.decay_half_life == 15


# ---------------------------------------------------------------------------
# New F-012: rate_factor tests
# ---------------------------------------------------------------------------

def _make_report(icir: float) -> FactorAuditReport:
    return FactorAuditReport(
        factor_name="test", ic_mean=0.0, ic_std=1.0, icir=icir,
        rank_ic_mean=0.0, turnover=0.0, decay_half_life=0,
        coverage=0.0, rating="",
    )


def test_rate_factor_a():
    assert rate_factor(_make_report(0.5)) == "A"
    assert rate_factor(_make_report(0.8)) == "A"
    assert rate_factor(_make_report(-0.6)) == "A"  # uses abs(icir)


def test_rate_factor_b():
    assert rate_factor(_make_report(0.3)) == "B"
    assert rate_factor(_make_report(0.4)) == "B"


def test_rate_factor_c():
    assert rate_factor(_make_report(0.1)) == "C"
    assert rate_factor(_make_report(0.2)) == "C"


def test_rate_factor_d():
    assert rate_factor(_make_report(0.0)) == "D"
    assert rate_factor(_make_report(0.05)) == "D"
    assert rate_factor(_make_report(-0.09)) == "D"
