"""Long-short spread calculation for quintile portfolio analysis.

Provides LongShortSpread to compute spread returns between top (Q5)
and bottom (Q1) quintiles, with optional benchmark comparison and
annualized metrics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# LongShortSpreadResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LongShortSpreadResult:
    """Immutable result of a long-short spread computation.

    Attributes:
        spread_returns: Per-period spread returns (Q5 - Q1).
        cumulative_spread: Cumulative spread returns.
        benchmark_returns: Per-period benchmark returns (aligned).
        excess_returns: Spread minus benchmark per period.
        annual_spread_return: Annualized spread return.
        annual_benchmark_return: Annualized benchmark return.
        annual_excess_return: Annual spread minus annual benchmark.
    """

    spread_returns: tuple[float, ...] = ()
    cumulative_spread: tuple[float, ...] = ()
    benchmark_returns: tuple[float, ...] = ()
    excess_returns: tuple[float, ...] = ()
    annual_spread_return: float = 0.0
    annual_benchmark_return: float = 0.0
    annual_excess_return: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "spread_returns": list(self.spread_returns),
            "cumulative_spread": list(self.cumulative_spread),
            "benchmark_returns": list(self.benchmark_returns),
            "excess_returns": list(self.excess_returns),
            "annual_spread_return": self.annual_spread_return,
            "annual_benchmark_return": self.annual_benchmark_return,
            "annual_excess_return": self.annual_excess_return,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LongShortSpreadResult:
        return cls(
            spread_returns=tuple(data.get("spread_returns", [])),
            cumulative_spread=tuple(data.get("cumulative_spread", [])),
            benchmark_returns=tuple(data.get("benchmark_returns", [])),
            excess_returns=tuple(data.get("excess_returns", [])),
            annual_spread_return=data.get("annual_spread_return", 0.0),
            annual_benchmark_return=data.get("annual_benchmark_return", 0.0),
            annual_excess_return=data.get("annual_excess_return", 0.0),
        )


# ---------------------------------------------------------------------------
# LongShortSpread
# ---------------------------------------------------------------------------


class LongShortSpread:
    """Compute long-short spread from quintile portfolio returns.

    The spread is defined as Q5 (top quintile) minus Q1 (bottom quintile)
    returns for each period. Optionally compares against a benchmark index.

    Args:
        benchmark_returns: Optional Series of benchmark returns indexed by date.
    """

    def __init__(self, benchmark_returns: Optional[pd.Series] = None) -> None:
        self._benchmark = benchmark_returns

    def compute(self, quintile_returns: pd.DataFrame) -> LongShortSpreadResult:
        """Compute spread returns and metrics from quintile returns.

        Args:
            quintile_returns: DataFrame with columns Q1..Q5 containing
                per-period quintile returns.

        Returns:
            LongShortSpreadResult with spread, cumulative, benchmark,
            and annualized metrics.
        """
        if quintile_returns.empty:
            return LongShortSpreadResult()

        q5 = quintile_returns["Q5"].values
        q1 = quintile_returns["Q1"].values
        spread = q5 - q1
        n = len(spread)

        # Cumulative spread
        cum = np.cumprod(1.0 + spread) - 1.0
        total_spread = float(cum[-1]) if n > 0 else 0.0

        # Annualized spread return
        annual_spread = float((1.0 + total_spread) ** (252.0 / n) - 1.0) if n > 0 else 0.0

        # Benchmark alignment
        benchmark_aligned: tuple[float, ...] = ()
        excess: tuple[float, ...] = ()
        annual_benchmark = 0.0
        annual_excess = 0.0

        if self._benchmark is not None and not self._benchmark.empty:
            bm = self._benchmark.reindex(quintile_returns.index).fillna(0.0).values
            excess_arr = spread - bm
            bm_cum = float(np.cumprod(1.0 + bm)[-1] - 1.0)
            annual_benchmark = float((1.0 + bm_cum) ** (252.0 / n) - 1.0) if n > 0 else 0.0
            annual_excess = annual_spread - annual_benchmark
            benchmark_aligned = tuple(bm.tolist())
            excess = tuple(excess_arr.tolist())

        return LongShortSpreadResult(
            spread_returns=tuple(spread.tolist()),
            cumulative_spread=tuple(cum.tolist()),
            benchmark_returns=benchmark_aligned,
            excess_returns=excess,
            annual_spread_return=annual_spread,
            annual_benchmark_return=annual_benchmark,
            annual_excess_return=annual_excess,
        )
