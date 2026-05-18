import re

import pandas as pd

from synapse.factor.spec import FactorSpec
from synapse.core.errors import FACTOR_COMPUTE_FAILED


def compute_factor(spec: FactorSpec, data: pd.DataFrame) -> pd.Series:
    """Compute factor values from data using spec.formula.

    For time-series formulas (shift/rolling), data is sorted by date within
    each ticker group, then the formula is evaluated per-group so shift()
    operates on each ticker's own history.
    For simple column expressions, pandas eval is used directly on the data.
    """
    try:
        formula = spec.formula

        if "shift(" in formula or "rolling(" in formula:
            result = _compute_timeseries_formula(data, formula)
        else:
            result = data.eval(formula)
            if isinstance(result, pd.Series):
                result.name = spec.factor_id
            return result.dropna()

        if isinstance(result, pd.Series):
            result.name = spec.factor_id
            return result.dropna()

        return pd.Series(result).dropna()
    except FACTOR_COMPUTE_FAILED:
        raise
    except Exception as e:
        raise FACTOR_COMPUTE_FAILED(
            f"Failed to compute factor {spec.factor_id}: {e}"
        )


def _compute_timeseries_formula(data: pd.DataFrame, formula: str) -> pd.Series:
    """Handle formulas with shift/rolling by evaluating per ticker group.

    Each ticker group is sorted by date, then the formula is evaluated
    using pandas eval so shift/rolling operates on a continuous time series.
    """
    # Identify which value column the formula references
    value_cols = [c for c in data.columns if c not in ("date", "ticker")]
    pivot_col = None
    for col in value_cols:
        if re.search(rf"\b{re.escape(col)}\b", formula):
            pivot_col = col
            break

    if pivot_col is None:
        raise FACTOR_COMPUTE_FAILED(
            f"Formula '{formula}' does not reference any data column "
            f"(available: {value_cols})"
        )

    # Sort by date so shift/rolling operates correctly
    sorted_data = data.sort_values("date")

    # Evaluate formula per ticker using groupby + apply
    results = []
    for ticker, group in sorted_data.groupby("ticker"):
        # Reset index so pandas eval can reference columns directly
        group = group.reset_index(drop=True)
        vals = group.eval(formula)
        # Build a Series with the original index from sorted_data
        idx = sorted_data[sorted_data["ticker"] == ticker].index
        series = pd.Series(vals.values, index=idx, name=pivot_col)
        results.append(series)

    return pd.concat(results)
