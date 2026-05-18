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

    def __post_init__(self):
        if self.transaction_cost_bps is None:
            raise ValueError("transaction_cost_bps must be explicitly set (no silent defaults)")
        if self.slippage_bps is None:
            raise ValueError("slippage_bps must be explicitly set (no silent defaults)")
