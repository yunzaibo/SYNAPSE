from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# F-015: Factor IC Decay Analysis
# ---------------------------------------------------------------------------

DECAY_THRESHOLDS: dict[str, tuple[int, int]] = {
    "fast_decay": (0, 5),
    "medium_decay": (5, 20),
    "slow_decay": (20, 60),
    "very_slow_decay": (60, 9999),
}


def compute_ic_decay(
    factor_values: pd.DataFrame | pd.Series,
    forward_returns: pd.DataFrame | pd.Series,
    max_lag: int = 60,
) -> pd.Series:
    """Compute IC at each lag from 0 to max_lag.

    For each lag *k* the forward returns are shifted by *k* periods, then
    the Pearson correlation with factor values is computed.  When the inputs
    are DataFrames the per-column ICs are averaged.

    Parameters
    ----------
    factor_values : pd.DataFrame | pd.Series
        Factor values indexed by date (and optionally by asset for DataFrames).
    forward_returns : pd.DataFrame | pd.Series
        Forward returns aligned with *factor_values*.
    max_lag : int
        Maximum lag in periods (default 60).

    Returns
    -------
    pd.Series
        IC values with index ``range(0, max_lag + 1)``.
    """
    ic_values: list[float] = []

    for lag in range(max_lag + 1):
        shifted_returns = forward_returns.shift(lag)
        ic_values.append(_compute_ic_for_lag(factor_values, shifted_returns))

    return pd.Series(ic_values, index=range(max_lag + 1), name="ic_decay")


def _compute_ic_for_lag(
    factor_values: pd.DataFrame | pd.Series,
    forward_returns: pd.DataFrame | pd.Series,
) -> float:
    """Compute mean IC across columns (DataFrame) or direct IC (Series)."""
    if isinstance(factor_values, pd.DataFrame) and isinstance(forward_returns, pd.DataFrame):
        ics = []
        for col in factor_values.columns:
            if col not in forward_returns.columns:
                continue
            aligned = pd.concat([factor_values[col], forward_returns[col]], axis=1).dropna()
            if len(aligned) < 2:
                continue
            ics.append(float(np.corrcoef(aligned.iloc[:, 0].values, aligned.iloc[:, 1].values)[0, 1]))
        return float(np.mean(ics)) if ics else 0.0

    # Series path
    aligned = pd.concat([factor_values, forward_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 0.0
    return float(np.corrcoef(aligned.iloc[:, 0].values, aligned.iloc[:, 1].values)[0, 1])


def compute_decay_half_life(ic_decay: pd.Series) -> int:
    """Compute the half-life of IC decay.

    The half-life is the first lag where |IC| drops below half of the
    peak |IC| (at lag 0).  If it never drops below half, returns the
    maximum lag present in the series.

    Parameters
    ----------
    ic_decay : pd.Series
        IC values indexed by lag (as returned by ``compute_ic_decay``).

    Returns
    -------
    int
        Lag at which IC halves (in periods).
    """
    if ic_decay.empty:
        return 0

    peak_ic = abs(ic_decay.iloc[0])
    if peak_ic == 0 or np.isnan(peak_ic):
        return 0

    half_peak = peak_ic / 2.0

    for lag in range(1, len(ic_decay)):
        if abs(ic_decay.iloc[lag]) < half_peak:
            return lag

    # Never dropped below half
    return int(ic_decay.index[-1])


def categorize_decay(half_life: int) -> str:
    """Categorize a half-life value into a decay category.

    Categories
    ----------
    - ``fast_decay``      : half-life < 5 days
    - ``medium_decay``    : 5 <= half-life < 20 days
    - ``slow_decay``      : 20 <= half-life < 60 days
    - ``very_slow_decay`` : half-life >= 60 days

    Parameters
    ----------
    half_life : int
        Half-life in periods.

    Returns
    -------
    str
        One of ``fast_decay``, ``medium_decay``, ``slow_decay``,
        ``very_slow_decay``.
    """
    if half_life < 5:
        return "fast_decay"
    if half_life < 20:
        return "medium_decay"
    if half_life < 60:
        return "slow_decay"
    return "very_slow_decay"
