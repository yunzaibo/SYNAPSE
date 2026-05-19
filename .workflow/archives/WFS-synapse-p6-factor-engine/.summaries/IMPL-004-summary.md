# Task: IMPL-004 Traditional Factors

## Implementation Summary

### Files Created
- `synapse/factor/factors/__init__.py` -- Package init, exports all 13 factor classes
- `synapse/factor/factors/momentum.py` -- Momentum1M, Momentum3M, Momentum6M1M
- `synapse/factor/factors/value.py` -- EP, BP, SP
- `synapse/factor/factors/quality.py` -- ROE, GrossMargin, DebtToAsset
- `synapse/factor/factors/volatility.py` -- RealizedVol20D, IdiosyncraticVol
- `synapse/factor/factors/liquidity.py` -- Turnover20D, AmihudIlliquidity

### Files Modified
- `synapse/factor/__init__.py` -- Added imports and exports for all 13 factor classes
- `tests/unit/test_traditional_factors.py` -- 83 tests covering all 13 factors

### Factor Classes

#### Momentum (category: "momentum")
- **Momentum1M** (`momentum.py`): Short-term reversal, `-(close / close.shift(20) - 1)`, lookback 20d
- **Momentum3M** (`momentum.py`): Medium-term momentum, `close / close.shift(60) - 1`, lookback 60d
- **Momentum6M1M** (`momentum.py`): Jegadeesh-Titman 6M-1M, `close.shift(120) / close.shift(20) - 1`, lookback 120d

#### Value (category: "value")
- **EP** (`value.py`): Earnings-to-price, `net_profit_ttm / market_cap`, lookback 1d
- **BP** (`value.py`): Book-to-price, `net_asset / market_cap`, lookback 1d
- **SP** (`value.py`): Sales-to-price, `revenue_ttm / market_cap`, lookback 1d

#### Quality (category: "quality")
- **ROE** (`quality.py`): Return on equity, `net_profit / net_asset`, lookback 1d
- **GrossMargin** (`quality.py`): Gross margin, `gross_profit / revenue`, lookback 1d
- **DebtToAsset** (`quality.py`): Debt-to-asset ratio, `total_debt / total_asset`, lookback 1d

#### Volatility (category: "volatility")
- **RealizedVol20D** (`volatility.py`): 20d realized vol, `daily_returns.rolling(20).std()`, lookback 20d
- **IdiosyncraticVol** (`volatility.py`): Idiosyncratic vol proxy, `residuals.rolling(60).std()`, lookback 60d

#### Liquidity (category: "liquidity")
- **Turnover20D** (`liquidity.py`): 20d avg turnover, `volume.rolling(20).mean() / float_shares`, lookback 20d
- **AmihudIlliquidity** (`liquidity.py`): Amihud illiquidity, `(abs(returns) / volume).rolling(20).mean()`, lookback 20d

## Outputs for Dependent Tasks

### Available Components
```python
from synapse.factor.factors import (
    Momentum1M, Momentum3M, Momentum6M1M,
    EP, BP, SP,
    ROE, GrossMargin, DebtToAsset,
    RealizedVol20D, IdiosyncraticVol,
    Turnover20D, AmihudIlliquidity,
)

# Or individually:
from synapse.factor.factors.momentum import Momentum1M
from synapse.factor.factors.value import EP
from synapse.factor.factors.quality import ROE
from synapse.factor.factors.volatility import RealizedVol20D
from synapse.factor.factors.liquidity import Turnover20D
```

### Integration Points
- **FactorRegistry.register()**: All 13 classes are BaseFactor subclasses, ready for registration
- **FactorEngine.compute_factor()**: Use factor_id strings (e.g., "momentum_1m") to compute
- **FactorEngine.compute_all()**: Compute all registered factors across tickers
- **FactorEngine.compute_batch()**: Compute selected factors by factor_id list

### Registration Example
```python
from synapse.factor.registry import FactorRegistry
from synapse.factor.factors import ALL_FACTOR_CLASSES  # or import individually

registry = FactorRegistry()
for cls in [Momentum1M, Momentum3M, Momentum6M1M, EP, BP, SP, ROE, GrossMargin, DebtToAsset, RealizedVol20D, IdiosyncraticVol, Turnover20D, AmihudIlliquidity]:
    registry.register(cls)
```

### Required DataFrame Columns
- Price factors: `close`
- Value factors: `net_profit_ttm`, `market_cap`, `net_asset`, `revenue_ttm`
- Quality factors: `net_profit`, `net_asset`, `gross_profit`, `revenue`, `total_debt`, `total_asset`
- Volatility factors: `close`
- Liquidity factors: `volume`, `float_shares`, `close`

## Status: Complete
