# P2 Long-Short Quintile Backtest Engine - Confirmed Guidance Specification

**Metadata**: 2026-05-19T23:30:00+08:00, workflow, quantitative-backtest, [system-architect, data-architect, subject-matter-expert]

## 1. Project Positioning & Goals

**CONFIRMED Objectives**: Build a long-short quintile backtest engine for A-share factor research, integrating with P6 FactorEngine to provide comprehensive performance metrics and attribution analysis.

**CONFIRMED Success Criteria**:
- 5-quintile portfolio sorting with long-short spread calculation
- 8 core performance metrics (annualized return, Sharpe ratio, max drawdown, win rate, profit/loss ratio, Calmar ratio, information ratio, turnover rate)
- Factor IC analysis integration with P6 FactorEngine
- Portfolio return attribution (factor exposure + residual)
- Support for point-in-time data validation

## 2. Concepts & Terminology

**Core Terms**: The following terms are used consistently throughout this specification.

| Term | Definition | Aliases | Category |
|------|------------|---------|----------|
| Quintile | Portfolio divided into 5 equal groups sorted by factor value | 五分位, quintile portfolio | core |
| Long-Short | Strategy going long top quintile and short bottom quintile | 多空策略, L/S | core |
| IC (Information Correlation) | Rank correlation between factor values and forward returns | 信息系数, RankIC | technical |
| ICIR (IC Information Ratio) | IC mean / IC standard deviation, measuring factor stability | IC信息比率 | technical |
| Sharpe Ratio | Risk-adjusted return measure (excess return / volatility) | 夏普比率 | technical |
| Max Drawdown | Maximum peak-to-trough decline in portfolio value | 最大回撤 | technical |
| Turnover Rate | Proportion of portfolio positions changed each period | 换手率 | technical |
| Factor Exposure | Portfolio's sensitivity to factor returns | 因子暴露 | technical |
| Attribution Analysis | Decomposing returns into factor and residual components | 收益归因 | business |

**Usage Rules**:
- All documents MUST use the canonical term
- Aliases are for reference only
- New terms introduced in role analysis MUST be added to this glossary

## 3. Non-Goals (Out of Scope)

The following are explicitly OUT of scope for this project:

- **Real-time trading execution**: This is a backtest engine, not a live trading system
- **Transaction cost modeling**: Simplified cost model (fixed bps), not full market impact model
- **Multi-asset classes**: Focus on A-share equities only, no futures/options/bonds
- **Machine learning factors**: Traditional quantitative factors only, ML-based factors deferred to future iterations
- **Intraday backtesting**: Daily frequency only, no minute-tick data support

**Rationale**: These exclusions help maintain focus on core objectives and prevent scope creep.

## 4. System Architect Decisions

### SELECTED Choices

**Backtest Engine Architecture**: The system MUST use event-driven architecture with separate data, signal, and execution layers
- **Rationale**: Enables flexible component composition and independent testing
- **Impact**: Each layer can be tested independently, supporting TDD approach
- **Requirement Level**: MUST

**Data Pipeline**: The system MUST support both batch and point-in-time (PIT) data access patterns
- **Rationale**: PIT validation is critical for avoiding look-ahead bias in factor research
- **Impact**: Data loader must support temporal queries with date filtering
- **Requirement Level**: MUST

**Performance Metrics**: The system MUST compute all 8 metrics in a single pass through return series
- **Rationale**:避免重复计算，提高效率
- **Impact**: MetricsCalculator must be stateful, accumulating statistics during iteration
- **Requirement Level**: MUST

### Cross-Role Considerations

**Integration with P6 FactorEngine**: The backtest engine MUST consume FactorEngine output (factor values, IC/RankIC) directly
- **Affected Roles**: system-architect, data-architect
- **Decision**: Use adapter pattern to bridge FactorEngine and BacktestEngine interfaces
- **Requirement Level**: MUST

## 5. Data Architect Decisions

### SELECTED Choices

**Data Model**: The system MUST use frozen dataclasses for all immutable data structures (BacktestResult, QuintilePortfolio, PerformanceMetrics)
- **Rationale**: Consistency with P1 Market Semantics patterns, thread safety
- **Impact**: All data objects are immutable after creation, supporting safe concurrent access
- **Requirement Level**: MUST

**Storage Format**: The system MUST persist backtest results in Parquet format for efficient columnar queries
- **Rationale**: Consistent with P1 market data storage, enables fast analytical queries
- **Impact**: Results can be queried by date range, factor, or metric without full load
- **Requirement Level**: MUST

**Factor Data Flow**: The system MUST accept factor values as DataFrame with MultiIndex (date, ticker)
- **Rationale**: Matches P6 FactorEngine output format, enables seamless integration
- **Impact**: No data transformation needed between factor computation and backtest
- **Requirement Level**: MUST

### Cross-Role Considerations

**Schema Compatibility**: All data models MUST be compatible with existing P1/P6 schemas
- **Affected Roles**: data-architect, system-architect
- **Decision**: Extend existing schemas where possible, create new schemas only for backtest-specific types
- **Requirement Level**: MUST

## 6. Subject Matter Expert Decisions

### SELECTED Choices

**Quintile Sorting**: The system MUST use equal-weight quintile sorting (20% per group)
- **Rationale**: Standard academic approach, most common in factor research literature
- **Impact**: Simple, reproducible methodology accepted by quantitative community
- **Requirement Level**: MUST

**Rebalancing Frequency**: The system MUST support configurable rebalancing periods (daily, weekly, monthly)
- **Rationale**: Different factors have different optimal holding periods
- **Impact**: User can specify rebalance_freq parameter, default to monthly
- **Requirement Level**: MUST

**Benchmark Comparison**: The system SHOULD compute excess returns relative to benchmark (default: CSI 300)
- **Rationale**: Quantitative researchers need to evaluate alpha generation
- **Impact**: MetricsCalculator must accept optional benchmark parameter
- **Requirement Level**: SHOULD

**Factor IC Analysis**: The system MUST compute rolling IC with configurable window (default: 20 days)
- **Rationale**: IC stability over time is critical for factor evaluation
- **Impact**: ICAnalyzer must support windowed computation with min_periods
- **Requirement Level**: MUST

### Cross-Role Considerations

**Return Attribution**: The system MUST decompose returns into factor exposure and residual components
- **Affected Roles**: subject-matter-expert, system-architect
- **Decision**: Use Barra-style factor model for attribution
- **Requirement Level**: MUST

## Cross-Role Integration

**CONFIRMED Integration Points**:
1. **P6 FactorEngine → BacktestEngine**: Factor values as DataFrame, IC/RankIC as Series
2. **P1 Market Semantics → BacktestEngine**: TradingCalendar for rebalancing dates, ExRightAdjustment for price adjustment
3. **BacktestEngine → Report**: PerformanceMetrics and AttributionResult for research report generation

## Risks & Constraints

**Identified Risks**:
1. **Data Quality**: Factor values may have missing data → Mitigation: Forward-fill with limit, skip tickers with insufficient data
2. **Computational Performance**: Large-scale backtests may be slow → Mitigation: Vectorized operations with NumPy/Pandas, optional parallel processing
3. **Look-ahead Bias**: Future data leakage in factor computation → Mitigation: PIT data access enforced, validation tests for temporal consistency

## Feature Decomposition

**Constraints**: Max 8 features | Each independently implementable | ID format: F-{3-digit}

| Feature ID | Name | Description | Related Roles | Priority |
|------------|------|-------------|---------------|----------|
| F-029 | quintile-portfolio-sorting | 5-quintile portfolio sorting with equal-weight allocation | subject-matter-expert, system-architect | High |
| F-030 | backtest-engine-core | Event-driven backtest engine with configurable rebalancing | system-architect, data-architect | High |
| F-031 | performance-metrics | 8 core metrics computation (annualized return, Sharpe, MDD, etc.) | subject-matter-expert, system-architect | High |
| F-032 | factor-ic-analysis | Rolling IC/RankIC/ICIR computation with configurable window | subject-matter-expert, data-architect | High |
| F-033 | return-attribution | Barra-style factor model return attribution | subject-matter-expert, system-architect | Medium |
| F-034 | backtest-result-persistence | Parquet storage for backtest results with query support | data-architect, system-architect | Medium |
| F-035 | long-short-spread | Long-short portfolio spread and cumulative return calculation | subject-matter-expert, system-architect | High |
| F-036 | backtest-integration-tests | End-to-end tests with P1/P6 integration | system-architect, data-architect | Medium |

## Appendix: Decision Tracking

| Decision ID | Category | Question | Selected | Phase | Rationale |
|-------------|----------|----------|----------|-------|-----------|
| D-001 | Intent | Project scope | P2 Backtest Engine | 1 | Core quantitative capability |
| D-002 | Roles | Role selection | system-architect, data-architect, subject-matter-expert | 2 | Technical + domain expertise |
| D-003 | System | Architecture | Event-driven with layered design | 3 | Flexibility and testability |
| D-004 | Data | Storage format | Parquet for results | 3 | Consistency with P1 |
| D-005 | Domain | Sorting method | Equal-weight quintile | 3 | Standard academic approach |
| D-006 | Integration | P6 integration | Adapter pattern | 4 | Seamless data flow |
