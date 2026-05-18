# Backtest Contract

## Purpose

Define backtest metadata, configuration, and metrics.

## P0 Implemented: BacktestConfig

```python
@dataclass
class BacktestConfig:
    universe: str
    benchmark: str
    start_date: str
    end_date: str
    rebalance_frequency: str    # daily | weekly | monthly
    transaction_cost_bps: float # REQUIRED — no silent defaults
    slippage_bps: float         # REQUIRED — no silent defaults
    position_limit: float
```

Source: `synapse/backtest/config.py`

**Governance**: `transaction_cost_bps` and `slippage_bps` must be explicitly set. Passing `None` raises `ValueError`.

## P0 Implemented: BacktestMetrics

```python
@dataclass
class BacktestMetrics:
    annual_return: float
    volatility: float
    sharpe: float
    max_drawdown: float
    turnover: float
    win_rate: float
    excess_return: float
    information_ratio: float
```

Source: `synapse/backtest/metrics.py`

## P0 Implemented: BacktestResult

```python
@dataclass
class BacktestResult:
    config: BacktestConfig
    metrics: BacktestMetrics
    portfolio_returns: list
    trades: list
    status: str             # running | succeeded | failed
```

Source: `synapse/backtest/engine.py`

## Rules

- Backtest assumptions must be explicit.
- Transaction cost must not be silently omitted.
- Date range must not be modified without a new experiment record.

## API

```python
from synapse.backtest.config import BacktestConfig
from synapse.backtest.engine import BacktestEngine

config = BacktestConfig(
    universe="equity", benchmark="ew", start_date="2024-01-01",
    end_date="2024-12-31", rebalance_frequency="monthly",
    transaction_cost_bps=10, slippage_bps=5,
)
engine = BacktestEngine()
result = engine.run_backtest(factor_values, forward_returns, config)
```
