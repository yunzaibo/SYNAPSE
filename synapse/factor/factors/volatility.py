from __future__ import annotations

import pandas as pd

from synapse.factor.base import BaseFactor
from synapse.factor.spec import FactorSpec


class RealizedVol20D(BaseFactor):
    """20-day realized volatility (rolling standard deviation of daily returns)."""

    @classmethod
    def factor_id(cls) -> str:
        return "realized_vol_20d"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="realized_vol_20d",
            name="20-Day Realized Volatility",
            description="Rolling 20-day standard deviation of daily returns",
            category="volatility",
            inputs=["close"],
            lookback_days=20,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        daily_returns = data["close"].pct_change()
        return daily_returns.rolling(20).std()

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["close"]


class IdiosyncraticVol(BaseFactor):
    """Idiosyncratic volatility (proxy: rolling std of returns minus mean)."""

    @classmethod
    def factor_id(cls) -> str:
        return "idiosyncratic_vol"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="idiosyncratic_vol",
            name="Idiosyncratic Volatility",
            description="Residual volatility after removing market component, proxy via rolling std of demeaned returns over 60 days",
            category="volatility",
            inputs=["close"],
            lookback_days=60,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        daily_returns = data["close"].pct_change()
        rolling_mean = daily_returns.rolling(60).mean()
        residuals = daily_returns - rolling_mean
        return residuals.rolling(60).std()

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["close"]
