from __future__ import annotations

import pandas as pd

from synapse.factor.base import BaseFactor
from synapse.factor.spec import FactorSpec


class Momentum1M(BaseFactor):
    """Short-term reversal factor (A-share specific: negative momentum)."""

    @classmethod
    def factor_id(cls) -> str:
        return "momentum_1m"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="momentum_1m",
            name="1-Month Momentum (Reversal)",
            description="Short-term reversal factor specific to A-share market",
            category="momentum",
            inputs=["close"],
            lookback_days=20,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return -(data["close"] / data["close"].shift(20) - 1)

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["close"]


class Momentum3M(BaseFactor):
    """3-month medium-term momentum factor."""

    @classmethod
    def factor_id(cls) -> str:
        return "momentum_3m"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="momentum_3m",
            name="3-Month Momentum",
            description="Medium-term price momentum over 3 months",
            category="momentum",
            inputs=["close"],
            lookback_days=60,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["close"] / data["close"].shift(60) - 1

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["close"]


class Momentum6M1M(BaseFactor):
    """Jegadeesh-Titman 6M-1M momentum factor."""

    @classmethod
    def factor_id(cls) -> str:
        return "momentum_6m_1m"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="momentum_6m_1m",
            name="6M-1M Momentum",
            description="Classic Jegadeesh-Titman momentum: 6-month return minus 1-month return",
            category="momentum",
            inputs=["close"],
            lookback_days=120,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["close"].shift(120) / data["close"].shift(20) - 1

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["close"]
