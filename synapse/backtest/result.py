"""Backtest result data models.

Defines frozen dataclasses for backtest outputs: QuintilePortfolio,
PerformanceMetrics, ICAnalysisResult, AttributionResult, BacktestResult.
All models are immutable (frozen=True, slots=True) for thread safety
and consistency with P1 AdjustmentEvent pattern.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Optional


# ---------------------------------------------------------------------------
# QuintilePortfolio
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QuintilePortfolio:
    """Quintile portfolio assignment for a single sorting date.

    Attributes:
        date: Portfolio construction date.
        quintiles: Mapping quintile_id (1-5) to list of ticker symbols.
        weights: Mapping quintile_id to {ticker: weight} dicts.
        factor_name: Identifier of the factor used for sorting.
        universe_size: Total number of stocks in the universe.
        valid_count: Number of stocks with valid factor values.
    """

    date: date
    quintiles: dict[int, tuple[str, ...]]
    weights: dict[int, dict[str, float]]
    factor_name: str
    universe_size: int
    valid_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "quintiles": {str(k): list(v) for k, v in self.quintiles.items()},
            "weights": self.weights,
            "factor_name": self.factor_name,
            "universe_size": self.universe_size,
            "valid_count": self.valid_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuintilePortfolio:
        quintiles = {int(k): tuple(v) for k, v in data["quintiles"].items()}
        weights = {int(k): v for k, v in data["weights"].items()}
        return cls(
            date=date.fromisoformat(data["date"]),
            quintiles=quintiles,
            weights=weights,
            factor_name=data["factor_name"],
            universe_size=data["universe_size"],
            valid_count=data["valid_count"],
        )


# ---------------------------------------------------------------------------
# PerformanceMetrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Standard performance metrics for a backtest run.

    14 fields covering return, risk, risk-adjusted return, and drawdown measures.
    All fields default to 0.0 for backward compatibility.
    """

    annual_return: float = 0.0
    volatility: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    turnover: float = 0.0
    win_rate: float = 0.0
    excess_return: float = 0.0
    information_ratio: float = 0.0
    calmar: float = 0.0
    profit_loss_ratio: float = 0.0
    long_short_spread: float = 0.0
    max_drawdown_duration: int = 0
    skewness: float = 0.0
    kurtosis: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerformanceMetrics:
        return cls(**{k: v for k, v in data.items() if k in cls.__slots__})


# ---------------------------------------------------------------------------
# ICAnalysisResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ICAnalysisResult:
    """Information Coefficient analysis results.

    Stores IC time series, rank IC time series, summary statistics,
    and optional rolling IC for a single factor.
    """

    factor_id: str
    ic_series: tuple[float, ...] = ()
    rank_ic_series: tuple[float, ...] = ()
    ic_mean: float = 0.0
    ic_std: float = 0.0
    icir: float = 0.0
    rank_ic_mean: float = 0.0
    rank_ic_std: float = 0.0
    rank_icir: float = 0.0
    rolling_ic: tuple[float, ...] = ()
    ic_positive_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "ic_series": list(self.ic_series),
            "rank_ic_series": list(self.rank_ic_series),
            "ic_mean": self.ic_mean,
            "ic_std": self.ic_std,
            "icir": self.icir,
            "rank_ic_mean": self.rank_ic_mean,
            "rank_ic_std": self.rank_ic_std,
            "rank_icir": self.rank_icir,
            "rolling_ic": list(self.rolling_ic),
            "ic_positive_ratio": self.ic_positive_ratio,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ICAnalysisResult:
        return cls(
            factor_id=data["factor_id"],
            ic_series=tuple(data.get("ic_series", [])),
            rank_ic_series=tuple(data.get("rank_ic_series", [])),
            ic_mean=data.get("ic_mean", 0.0),
            ic_std=data.get("ic_std", 0.0),
            icir=data.get("icir", 0.0),
            rank_ic_mean=data.get("rank_ic_mean", 0.0),
            rank_ic_std=data.get("rank_ic_std", 0.0),
            rank_icir=data.get("rank_icir", 0.0),
            rolling_ic=tuple(data.get("rolling_ic", [])),
            ic_positive_ratio=data.get("ic_positive_ratio", 0.0),
        )


# ---------------------------------------------------------------------------
# AttributionResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AttributionResult:
    """Factor return attribution analysis results.

    Stores factor returns by quintile, residual returns, and model fit.
    """

    factor_returns: dict[int, float] = field(default_factory=dict)
    residual_returns: tuple[float, ...] = ()
    total_factor_return: float = 0.0
    residual_return: float = 0.0
    r_squared: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_returns": self.factor_returns,
            "residual_returns": list(self.residual_returns),
            "total_factor_return": self.total_factor_return,
            "residual_return": self.residual_return,
            "r_squared": self.r_squared,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttributionResult:
        return cls(
            factor_returns=data.get("factor_returns", {}),
            residual_returns=tuple(data.get("residual_returns", [])),
            total_factor_return=data.get("total_factor_return", 0.0),
            residual_return=data.get("residual_return", 0.0),
            r_squared=data.get("r_squared", 0.0),
        )


# ---------------------------------------------------------------------------
# BacktestResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BacktestRunResult:
    """Top-level container for all backtest outputs.

    Aggregates quintile portfolios, returns, performance metrics,
    IC analysis, and attribution into a single immutable record.

    Note: This is distinct from ``BacktestEngine.BacktestResult`` (mutable),
    which is the engine's internal run record.
    """

    id: str
    schema_version: str = "1.0"
    config: dict[str, Any] = field(default_factory=dict)
    run_timestamp: str = ""
    start_date: str = ""
    end_date: str = ""
    factor_id: str = ""
    quintile_portfolios: tuple[QuintilePortfolio, ...] = ()
    quintile_returns: dict[int, float] = field(default_factory=dict)
    long_short_returns: tuple[float, ...] = ()
    benchmark_returns: tuple[float, ...] = ()
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    ic_analysis: Optional[ICAnalysisResult] = None
    attribution: Optional[AttributionResult] = None
    status: str = "pending"
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "schema_version": self.schema_version,
            "config": self.config,
            "run_timestamp": self.run_timestamp,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "factor_id": self.factor_id,
            "quintile_portfolios": [qp.to_dict() for qp in self.quintile_portfolios],
            "quintile_returns": self.quintile_returns,
            "long_short_returns": list(self.long_short_returns),
            "benchmark_returns": list(self.benchmark_returns),
            "performance": self.performance.to_dict(),
            "ic_analysis": self.ic_analysis.to_dict() if self.ic_analysis else None,
            "attribution": self.attribution.to_dict() if self.attribution else None,
            "status": self.status,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BacktestRunResult:
        qp_list = [
            QuintilePortfolio.from_dict(qp) for qp in data.get("quintile_portfolios", [])
        ]
        perf_data = data.get("performance", {})
        ic_data = data.get("ic_analysis")
        attr_data = data.get("attribution")
        return cls(
            id=data["id"],
            schema_version=data.get("schema_version", "1.0"),
            config=data.get("config", {}),
            run_timestamp=data.get("run_timestamp", ""),
            start_date=data.get("start_date", ""),
            end_date=data.get("end_date", ""),
            factor_id=data.get("factor_id", ""),
            quintile_portfolios=tuple(qp_list),
            quintile_returns=data.get("quintile_returns", {}),
            long_short_returns=tuple(data.get("long_short_returns", [])),
            benchmark_returns=tuple(data.get("benchmark_returns", [])),
            performance=PerformanceMetrics.from_dict(perf_data) if perf_data else PerformanceMetrics(),
            ic_analysis=ICAnalysisResult.from_dict(ic_data) if ic_data else None,
            attribution=AttributionResult.from_dict(attr_data) if attr_data else None,
            status=data.get("status", "pending"),
            error=data.get("error"),
        )
