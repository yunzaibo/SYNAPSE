from __future__ import annotations

import pandas as pd

from synapse.factor.base import BaseFactor
from synapse.factor.spec import FactorSpec


class EP(BaseFactor):
    """Earnings-to-price ratio (inverse P/E, TTM)."""

    @classmethod
    def factor_id(cls) -> str:
        return "ep"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="ep",
            name="Earnings-to-Price",
            description="TTM net profit divided by market cap (inverse P/E)",
            category="value",
            inputs=["net_profit_ttm", "market_cap"],
            lookback_days=1,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["net_profit_ttm"] / data["market_cap"]

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["net_profit_ttm", "market_cap"]


class BP(BaseFactor):
    """Book-to-price ratio (inverse P/B)."""

    @classmethod
    def factor_id(cls) -> str:
        return "bp"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="bp",
            name="Book-to-Price",
            description="Net asset divided by market cap (inverse P/B)",
            category="value",
            inputs=["net_asset", "market_cap"],
            lookback_days=1,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["net_asset"] / data["market_cap"]

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["net_asset", "market_cap"]


class SP(BaseFactor):
    """Sales-to-price ratio (inverse P/S)."""

    @classmethod
    def factor_id(cls) -> str:
        return "sp"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="sp",
            name="Sales-to-Price",
            description="TTM revenue divided by market cap (inverse P/S)",
            category="value",
            inputs=["revenue_ttm", "market_cap"],
            lookback_days=1,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["revenue_ttm"] / data["market_cap"]

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["revenue_ttm", "market_cap"]
