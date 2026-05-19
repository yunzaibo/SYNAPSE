from __future__ import annotations

import pandas as pd

from synapse.factor.base import BaseFactor
from synapse.factor.spec import FactorSpec


class ROE(BaseFactor):
    """Return on equity (net profit / net asset)."""

    @classmethod
    def factor_id(cls) -> str:
        return "roe"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="roe",
            name="Return on Equity",
            description="Core quality indicator: net profit divided by net asset",
            category="quality",
            inputs=["net_profit", "net_asset"],
            lookback_days=1,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["net_profit"] / data["net_asset"]

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["net_profit", "net_asset"]


class GrossMargin(BaseFactor):
    """Gross profit margin ratio."""

    @classmethod
    def factor_id(cls) -> str:
        return "gross_margin"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="gross_margin",
            name="Gross Margin",
            description="Gross profit divided by revenue, stable quality indicator",
            category="quality",
            inputs=["gross_profit", "revenue"],
            lookback_days=1,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["gross_profit"] / data["revenue"]

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["gross_profit", "revenue"]


class DebtToAsset(BaseFactor):
    """Debt-to-asset ratio (lower is better)."""

    @classmethod
    def factor_id(cls) -> str:
        return "debt_to_asset"

    @classmethod
    def spec(cls) -> FactorSpec:
        return FactorSpec(
            factor_id="debt_to_asset",
            name="Debt-to-Asset Ratio",
            description="Total debt divided by total asset (lower value indicates better quality)",
            category="quality",
            inputs=["total_debt", "total_asset"],
            lookback_days=1,
            data_source="eastmoney",
            publication_lag=1,
            compute_fn=None,
        )

    def compute(self, data: pd.DataFrame) -> pd.Series:
        return data["total_debt"] / data["total_asset"]

    @classmethod
    def required_columns(cls) -> list[str]:
        return ["total_debt", "total_asset"]
