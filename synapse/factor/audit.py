from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


# ---------------------------------------------------------------------------
# New F-012: IC / RankIC Auditor
# ---------------------------------------------------------------------------

@dataclass
class FactorAuditReport:
    """Comprehensive audit report for a factor (F-012)."""

    factor_name: str
    ic_mean: float              # mean IC over periods
    ic_std: float               # std of IC over periods
    icir: float                 # ICIR = ic_mean / ic_std
    rank_ic_mean: float         # mean RankIC
    turnover: float             # factor turnover rate
    decay_half_life: int        # IC decay half-life in days
    coverage: float             # industry coverage ratio
    rating: str                 # "A" | "B" | "C" | "D"


def compute_ic(factor_values: pd.Series, forward_returns: pd.Series) -> float:
    """Pearson IC: linear correlation between factor values and forward returns."""
    aligned = pd.concat([factor_values, forward_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 0.0
    return round(float(np.corrcoef(aligned.iloc[:, 0].values, aligned.iloc[:, 1].values)[0, 1]), 6)


def compute_rank_ic(factor_values: pd.Series, forward_returns: pd.Series) -> float:
    """Spearman RankIC: rank correlation between factor values and forward returns."""
    aligned = pd.concat([factor_values, forward_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 0.0
    rho, _ = spearmanr(aligned.iloc[:, 0].values, aligned.iloc[:, 1].values)
    return round(float(rho), 6)


def compute_rolling_ic(factor_series: pd.DataFrame, window: int = 60) -> pd.Series:
    """Rolling-window IC across a DataFrame of factor/return pairs.

    Parameters
    ----------
    factor_series : pd.DataFrame
        Must contain columns ``"factor"`` and ``"forward_return"``.
    window : int
        Rolling window size (default 60 trading days).

    Returns
    -------
    pd.Series
        Rolling Pearson IC values (index aligned with input).
    """
    df = factor_series.dropna(subset=["factor", "forward_return"]).reset_index(drop=True)
    if len(df) < window:
        return pd.Series(dtype=float, name="rolling_ic")

    fv = df["factor"].values
    fr = df["forward_return"].values
    n = len(fv)
    ic_values = np.full(n, np.nan)

    for i in range(window - 1, n):
        fv_win = fv[i - window + 1 : i + 1]
        fr_win = fr[i - window + 1 : i + 1]
        ic_values[i] = np.corrcoef(fv_win, fr_win)[0, 1]

    result = pd.Series(ic_values, index=df.index, name="rolling_ic")
    return result


def compute_icir(ic_mean: float, ic_std: float) -> float:
    """ICIR = IC mean / IC std (stability-adjusted IC)."""
    if ic_std == 0 or np.isnan(ic_std):
        return 0.0
    return round(ic_mean / ic_std, 4)


def rate_factor(report: FactorAuditReport) -> str:
    """Rate a factor based on its ICIR (A/B/C/D)."""
    icir = abs(report.icir)
    if icir >= 0.5:
        return "A"
    if icir >= 0.3:
        return "B"
    if icir >= 0.1:
        return "C"
    return "D"


# ---------------------------------------------------------------------------
# Legacy audit (kept for backward compatibility)
# ---------------------------------------------------------------------------

@dataclass
class FactorAuditResult:
    factor_id: str
    version: str
    coverage: float  # % of non-NaN values
    missing_rate: float  # % of NaN values
    ic: float  # Pearson correlation with forward returns
    rank_ic: float  # Spearman rank correlation with forward returns
    leakage_risk: str  # low | medium | high | unknown
    notes: str = ""


def audit_factor(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    factor_id: str = "",
    version: str = "1.0",
) -> FactorAuditResult:
    """Audit a factor against forward returns."""
    # Align indices
    aligned = pd.concat([factor_values, forward_returns], axis=1).dropna()
    if len(aligned) < 10:
        return FactorAuditResult(
            factor_id=factor_id,
            version=version,
            coverage=0.0,
            missing_rate=1.0,
            ic=0.0,
            rank_ic=0.0,
            leakage_risk="unknown",
            notes="Insufficient data for audit",
        )

    fv = aligned.iloc[:, 0]
    fr = aligned.iloc[:, 1]

    coverage = len(fv) / len(factor_values) if len(factor_values) > 0 else 0
    missing_rate = 1 - coverage

    ic = float(np.corrcoef(fv.values, fr.values)[0, 1]) if len(fv) > 1 else 0.0
    rank_ic_val, _ = spearmanr(fv.values, fr.values) if len(fv) > 1 else (0.0, 1.0)

    # Simple leakage heuristic: if IC > 0.95, flag as high risk
    leakage_risk = "low"
    if abs(ic) > 0.95:
        leakage_risk = "high"
    elif abs(ic) > 0.8:
        leakage_risk = "medium"

    return FactorAuditResult(
        factor_id=factor_id,
        version=version,
        coverage=round(coverage, 4),
        missing_rate=round(missing_rate, 4),
        ic=round(float(ic), 4),
        rank_ic=round(float(rank_ic_val), 4),
        leakage_risk=leakage_risk,
    )
