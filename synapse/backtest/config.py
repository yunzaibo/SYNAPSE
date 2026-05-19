from dataclasses import dataclass


@dataclass
class BacktestConfig:
    universe: str
    benchmark: str
    start_date: str
    end_date: str
    rebalance_frequency: str  # daily | weekly | monthly
    transaction_cost_bps: float  # REQUIRED — must be explicitly set
    slippage_bps: float  # REQUIRED — must be explicitly set
    position_limit: float = 1.0  # max weight per position
    n_quintiles: int = 5
    ic_window: int = 20
    ic_min_periods: int = 10
    enable_attribution: bool = True
    enable_ic_analysis: bool = True
    output_dir: str = "backtests/"

    def __post_init__(self):
        if self.transaction_cost_bps is None:
            raise ValueError("transaction_cost_bps must be explicitly set (no silent defaults)")
        if self.slippage_bps is None:
            raise ValueError("slippage_bps must be explicitly set (no silent defaults)")
        if self.n_quintiles < 2:
            raise ValueError(f"n_quintiles must be >= 2, got {self.n_quintiles}")
        if self.rebalance_frequency not in ("daily", "weekly", "monthly"):
            raise ValueError(
                f"rebalance_frequency must be 'daily', 'weekly', or 'monthly', "
                f"got '{self.rebalance_frequency}'"
            )
