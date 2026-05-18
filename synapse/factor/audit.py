from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


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
