from __future__ import annotations

import pandas as pd

from synapse.factor.base import BaseFactor
from synapse.factor.spec import FactorSpec


class Turnover20D(BaseFactor):
    """20-day average turnover ratio."""

    @classmethod
    def factor_id(cls) -> str:
        return "turnover_20d"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="turnover_20d",
            name="20-Day Average Turnover",
            description="Rolling 20-day average of volume divided by float shares",
            category="liquidity",
            inputs=["volume", "float_shares"],
            lookback_days=20,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["volume"].rolling(20).mean() / data["float_shares"]

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["volume", "float_shares"]


class AmihudIlliquidity(BaseFactor):
    """Amihud illiquidity ratio (20-day rolling average)."""

    @classmethod
    def factor_id(cls) -> str:
        return "amihud_illiquidity"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="amihud_illiquidity",
            name="Amihud Illiquidity",
            description="Rolling 20-day average of absolute daily return divided by volume",
            category="liquidity",
            inputs=["close", "volume"],
            lookback_days=20,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        daily_returns = data["close"].pct_change()
        illiq = daily_returns.abs() / data["volume"]
        return illiq.rolling(20).mean()

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["close", "volume"]
