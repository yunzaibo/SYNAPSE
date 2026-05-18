"""Integration test: full P0 research pipeline."""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from synapse.data.loader import load_dataset
from synapse.data.validator import validate_metadata
from synapse.factor.spec import FactorSpec
from synapse.factor.compute import compute_factor
from synapse.factor.audit import audit_factor
from synapse.experiment.tracker import ExperimentTracker
from synapse.backtest.config import BacktestConfig
from synapse.backtest.engine import BacktestEngine
from synapse.report.generator import generate_report


BASE = Path(__file__).parent.parent.parent


@pytest.fixture
def sample_data():
    df, meta = load_dataset(
        BASE / "data/sample/sample_prices.csv",
        BASE / "data/sample/sample_prices.yaml",
    )
    return df, meta


@pytest.fixture
def factor_spec():
    return FactorSpec.from_yaml(BASE / "factors/sample_momentum.yaml")


class TestFullPipeline:
    def test_load_data(self, sample_data):
        df, meta = sample_data
        assert len(df) == 100
        assert meta.dataset_id == "sample-prices"

    def test_validate_metadata(self, sample_data):
        _, meta = sample_data
        errors = validate_metadata(meta)
        assert errors == []

    def test_compute_factor(self, sample_data, factor_spec):
        df, _ = sample_data
        values = compute_factor(factor_spec, df)
        assert len(values) > 0

    def test_audit_factor(self, sample_data, factor_spec):
        df, _ = sample_data
        values = compute_factor(factor_spec, df)

        df_sorted = df.sort_values(["ticker", "date"])
        df_sorted["fwd_ret"] = df_sorted.groupby("ticker")["close"].pct_change().shift(-1)
        fwd = df_sorted.set_index(["date", "ticker"])["fwd_ret"].dropna()

        aligned_v = values.reindex(fwd.index).dropna()
        aligned_r = fwd.reindex(aligned_v.index).dropna()
        common = aligned_v.index.intersection(aligned_r.index)

        result = audit_factor(aligned_v.loc[common], aligned_r.loc[common])
        assert 0 <= result.coverage <= 1
        assert isinstance(result.ic, float)
        assert isinstance(result.rank_ic, float)

    def test_experiment_lifecycle(self, tmp_path):
        tracker = ExperimentTracker(tmp_path)
        exp = tracker.create_experiment(
            name="test", data_version="v1", factor_version="v1",
            parameters={}, created_by="human",
        )
        assert exp.status == "draft"

        updated = tracker.update_status(exp.experiment_id, "running")
        assert updated.status == "running"

        with pytest.raises(Exception):
            tracker.delete_experiment(exp.experiment_id)

    def test_backtest_run(self, sample_data, factor_spec):
        df, meta = sample_data
        values = compute_factor(factor_spec, df)

        df_sorted = df.sort_values(["ticker", "date"])
        df_sorted["fwd_ret"] = df_sorted.groupby("ticker")["close"].pct_change().shift(-1)
        fwd = df_sorted.set_index(["date", "ticker"])["fwd_ret"].dropna()

        aligned_v = values.reindex(fwd.index).dropna()
        aligned_r = fwd.reindex(aligned_v.index).dropna()
        common = aligned_v.index.intersection(aligned_r.index)

        config = BacktestConfig(
            universe="test", benchmark="ew", start_date="2024-01-01",
            end_date="2024-05-10", rebalance_frequency="monthly",
            transaction_cost_bps=10, slippage_bps=5,
        )
        engine = BacktestEngine()
        result = engine.run_backtest(aligned_v.loc[common], aligned_r.loc[common], config)
        assert result.status in ("succeeded", "failed")

    def test_generate_report(self):
        report = generate_report(None, None, None, None)
        assert "## Hypothesis" in report
        assert "## Results" in report
        assert "## Conclusion" in report

    def test_end_to_end(self, sample_data, factor_spec, tmp_path):
        """Full pipeline: data -> factor -> audit -> experiment -> backtest -> report."""
        df, meta = sample_data

        # Factor
        values = compute_factor(factor_spec, df)

        # Forward returns
        df_sorted = df.sort_values(["ticker", "date"])
        df_sorted["fwd_ret"] = df_sorted.groupby("ticker")["close"].pct_change().shift(-1)
        fwd = df_sorted.set_index(["date", "ticker"])["fwd_ret"].dropna()
        aligned_v = values.reindex(fwd.index).dropna()
        aligned_r = fwd.reindex(aligned_v.index).dropna()
        common = aligned_v.index.intersection(aligned_r.index)

        # Audit
        audit = audit_factor(aligned_v.loc[common], aligned_r.loc[common],
                            factor_id=factor_spec.factor_id)

        # Experiment
        tracker = ExperimentTracker(tmp_path)
        exp = tracker.create_experiment(
            name="E2E Test", data_version=meta.dataset_id,
            factor_version=factor_spec.version,
            parameters={"cost_bps": 10}, created_by="ai",
        )
        tracker.update_status(exp.experiment_id, "running")

        # Backtest
        config = BacktestConfig(
            universe="test", benchmark="ew", start_date="2024-01-01",
            end_date="2024-05-10", rebalance_frequency="monthly",
            transaction_cost_bps=10, slippage_bps=5,
        )
        bt = BacktestEngine().run_backtest(aligned_v.loc[common], aligned_r.loc[common], config)
        tracker.update_status(exp.experiment_id, bt.status)

        # Report
        report = generate_report(exp, factor_spec, audit, bt)
        assert "## Hypothesis" in report
        assert "## Results" in report
        assert "## Conclusion" in report
