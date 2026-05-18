import numpy as np
import pandas as pd

from synapse.factor.audit import audit_factor, FactorAuditResult


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
