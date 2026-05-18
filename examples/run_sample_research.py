#!/usr/bin/env python3
"""SYNAPSE P0 Research Pipeline Demo.

Complete research loop: load data -> define factor -> audit -> experiment -> backtest -> report.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from synapse.data.loader import load_dataset
from synapse.data.validator import validate_metadata
from synapse.factor.spec import FactorSpec
from synapse.factor.compute import compute_factor
from synapse.factor.audit import audit_factor
from synapse.experiment.tracker import ExperimentTracker
from synapse.backtest.config import BacktestConfig
from synapse.backtest.engine import BacktestEngine
from synapse.report.generator import generate_report


def main():
    base = Path(__file__).parent.parent

    # Step 1: Load sample data
    print("Step 1: Loading sample data...")
    df, metadata = load_dataset(
        base / "data/sample/sample_prices.csv",
        base / "data/sample/sample_prices.yaml",
    )
    errors = validate_metadata(metadata)
    if errors:
        print(f"  WARNING: Metadata validation errors: {errors}")
    print(f"  Loaded {len(df)} rows, tickers: {df['ticker'].unique().tolist()}")

    # Step 2: Load factor spec
    print("\nStep 2: Loading factor spec...")
    factor_spec = FactorSpec.from_yaml(base / "factors/sample_momentum.yaml")
    print(f"  Factor: {factor_spec.name} ({factor_spec.factor_id})")
    print(f"  Formula: {factor_spec.formula}")

    # Step 3: Compute factor values
    print("\nStep 3: Computing factor values...")
    factor_values = compute_factor(factor_spec, df)
    print(f"  Computed {len(factor_values)} factor values")

    # Step 4: Audit factor
    print("\nStep 4: Auditing factor...")
    # Create forward returns (next-day return per ticker)
    df_sorted = df.sort_values(["ticker", "date"])
    df_sorted["forward_return"] = df_sorted.groupby("ticker")["close"].pct_change().shift(-1)
    forward_returns = df_sorted.set_index(["date", "ticker"])["forward_return"].dropna()

    # Align factor values with forward returns
    aligned_factor = factor_values.reindex(forward_returns.index).dropna()
    aligned_returns = forward_returns.reindex(aligned_factor.index).dropna()
    common_idx = aligned_factor.index.intersection(aligned_returns.index)

    audit_result = audit_factor(
        aligned_factor.loc[common_idx],
        aligned_returns.loc[common_idx],
        factor_id=factor_spec.factor_id,
        version=factor_spec.version,
    )
    print(f"  IC: {audit_result.ic}, RankIC: {audit_result.rank_ic}")
    print(f"  Coverage: {audit_result.coverage}, Leakage: {audit_result.leakage_risk}")

    # Step 5: Create experiment record
    print("\nStep 5: Creating experiment record...")
    tracker = ExperimentTracker(base / "experiments")
    experiment = tracker.create_experiment(
        name="Momentum-20d Backtest",
        data_version=metadata.dataset_id,
        factor_version=factor_spec.version,
        parameters={"transaction_cost_bps": 10, "slippage_bps": 5},
        created_by="ai",
    )
    tracker.update_status(experiment.experiment_id, "running")
    print(f"  Experiment: {experiment.experiment_id}")

    # Step 6: Run backtest
    print("\nStep 6: Running backtest...")
    config = BacktestConfig(
        universe="sample-equity",
        benchmark="equal-weight",
        start_date=metadata.start_date,
        end_date=metadata.end_date,
        rebalance_frequency="monthly",
        transaction_cost_bps=10,
        slippage_bps=5,
    )

    engine = BacktestEngine()
    backtest_result = engine.run_backtest(
        aligned_factor.loc[common_idx],
        aligned_returns.loc[common_idx],
        config,
    )

    tracker.update_status(experiment.experiment_id, backtest_result.status)
    print(f"  Status: {backtest_result.status}")
    if backtest_result.metrics:
        m = backtest_result.metrics
        print(f"  Sharpe: {m.sharpe}, MaxDD: {m.max_drawdown}, Annual Return: {m.annual_return}")

    # Step 7: Generate report
    print("\nStep 7: Generating report...")
    report = generate_report(experiment, factor_spec, audit_result, backtest_result)

    report_path = base / "reports" / "sample-research-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"  Report saved to: {report_path}")

    # Summary
    print("\n" + "=" * 60)
    print("P0 Research Pipeline Complete!")
    print(f"  Data: {len(df)} rows, {metadata.start_date} to {metadata.end_date}")
    print(f"  Factor: {factor_spec.name} (v{factor_spec.version})")
    print(f"  Audit: IC={audit_result.ic}, RankIC={audit_result.rank_ic}")
    print(f"  Backtest: Sharpe={backtest_result.metrics.sharpe}")
    print(f"  Report: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
