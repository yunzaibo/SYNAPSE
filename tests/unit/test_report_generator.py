"""Tests for synapse.report.generator — markdown report generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from synapse.report.generator import generate_report, _determine_verdict


# ---------------------------------------------------------------------------
# Minimal mock objects (avoid importing heavy deps)
# ---------------------------------------------------------------------------

def _make_experiment(**overrides: Any):
    """Create a minimal ExperimentRecord-like object."""
    defaults = dict(
        experiment_id="exp-001",
        name="Momentum Factor Test",
        research_task_id="task-001",
        data_version="v2",
        factor_version="v3",
        model_version="m1",
        split_method="time_series",
        parameters={"lookback": 20},
        started_at="2025-01-01",
        completed_at="2025-01-15",
        status="completed",
        artifacts=["plot.png"],
        created_by="human",
    )
    defaults.update(overrides)

    @dataclass
    class _FakeExperiment:
        experiment_id: str = ""
        name: str = ""
        research_task_id: str = ""
        data_version: str = ""
        factor_version: str = ""
        model_version: str = ""
        split_method: str = ""
        parameters: dict = field(default_factory=dict)
        started_at: str = ""
        completed_at: str = ""
        status: str = ""
        artifacts: list = field(default_factory=list)
        created_by: str = ""

    return _FakeExperiment(**defaults)


def _make_factor_spec(**overrides: Any):
    """Create a minimal FactorSpec-like object."""
    defaults = dict(
        factor_id="fct-001",
        name="Momentum 20d",
        description="20-day price momentum",
        domain="cross_sectional_equity",
        inputs=["close"],
        formula="close / close.shift(20) - 1",
        frequency="daily",
        direction="positive",
        universe="CSI300",
        created_by="ai",
        version="1.0",
    )
    defaults.update(overrides)

    @dataclass
    class _FakeFactorSpec:
        factor_id: str = ""
        name: str = ""
        description: str = ""
        domain: str = ""
        inputs: list = field(default_factory=list)
        formula: str = ""
        frequency: str = ""
        direction: str = ""
        universe: str = ""
        created_by: str = ""
        version: str = "1.0"

    return _FakeFactorSpec(**defaults)


def _make_audit_result(**overrides: Any):
    """Create a minimal FactorAuditResult-like object."""
    defaults = dict(
        factor_id="fct-001",
        version="1.0",
        coverage=0.95,
        missing_rate=0.05,
        ic=0.03,
        rank_ic=0.04,
        leakage_risk="low",
        notes="",
    )
    defaults.update(overrides)

    @dataclass
    class _FakeAuditResult:
        factor_id: str = ""
        version: str = ""
        coverage: float = 0.0
        missing_rate: float = 0.0
        ic: float = 0.0
        rank_ic: float = 0.0
        leakage_risk: str = ""
        notes: str = ""

    return _FakeAuditResult(**defaults)


def _make_backtest_result(**overrides: Any):
    """Create a minimal BacktestResult-like object."""
    defaults = dict(
        config=None,
        metrics=None,
        portfolio_returns=[0.01, -0.005, 0.02],
        trades=[],
        status="completed",
    )
    defaults.update(overrides)

    @dataclass
    class _FakeMetrics:
        annual_return: float = 0.0
        volatility: float = 0.0
        sharpe: float = 0.0
        max_drawdown: float = 0.0
        turnover: float = 0.0
        win_rate: float = 0.0
        excess_return: float = 0.0
        information_ratio: float = 0.0

    @dataclass
    class _FakeBacktestResult:
        config: Any = None
        metrics: Any = None
        portfolio_returns: list = field(default_factory=list)
        trades: list = field(default_factory=list)
        status: str = "running"

    result = _FakeBacktestResult(**{k: v for k, v in defaults.items() if k != "metrics"})
    if "metrics" in overrides and overrides["metrics"] is not None:
        result.metrics = _FakeMetrics(**overrides["metrics"])
    elif defaults["metrics"] is not None:
        result.metrics = _FakeMetrics(**defaults["metrics"])
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateReportAllNone:
    """generate_report with all None inputs."""

    def test_all_sections_present(self):
        report = generate_report(None, None, None, None)

        # All 10 required sections
        assert "# Untitled Research" in report
        assert "## Hypothesis" in report
        assert "## Data" in report
        assert "## Factor Definition" in report
        assert "## Validation Method" in report
        assert "## Experiment Setup" in report
        assert "## Results" in report
        assert "## Risk Review" in report
        assert "## Conclusion" in report
        assert "## Next Experiments" in report

    def test_fallback_messages(self):
        report = generate_report(None, None, None, None)

        assert "No factor specification provided" in report
        assert "No experiment data available" in report
        assert "No audit results available" in report
        assert "No backtest results available" in report
        assert "No experiment setup available" in report

    def test_verdict_inconclusive_when_no_data(self):
        report = generate_report(None, None, None, None)
        assert "Conclusion: inconclusive" in report

    def test_artifacts_section_present(self):
        report = generate_report(None, None, None, None)
        assert "## Artifacts" in report
        assert "Report generated by SYNAPSE research pipeline" in report


class TestGenerateReportWithMockData:
    """generate_report with realistic mock data."""

    def test_title_from_experiment(self):
        exp = _make_experiment(name="Alpha Factor Study")
        report = generate_report(exp, None, None, None)
        assert "# Alpha Factor Study" in report

    def test_hypothesis_from_factor_spec(self):
        spec = _make_factor_spec(
            name="Value Ratio",
            factor_id="fct-val-001",
            domain="cross_sectional_equity",
            formula="book_value / market_cap",
            direction="positive",
            universe="CSI500",
        )
        report = generate_report(None, spec, None, None)

        assert "Value Ratio" in report
        assert "fct-val-001" in report
        assert "cross_sectional_equity" in report
        assert "`book_value / market_cap`" in report
        assert "positive" in report

    def test_data_section_from_experiment(self):
        exp = _make_experiment(data_version="v5", factor_version="v3")
        report = generate_report(exp, None, None, None)

        assert "Data version: v5" in report
        assert "Factor version: v3" in report

    def test_factor_definition_table(self):
        spec = _make_factor_spec()
        report = generate_report(None, spec, None, None)

        # Table headers present
        assert "| Field | Value |" in report
        assert "| Factor ID | fct-001 |" in report
        assert "| Name | Momentum 20d |" in report
        assert "| Frequency | daily |" in report

    def test_validation_method_from_audit(self):
        audit = _make_audit_result(ic=0.06, rank_ic=0.07, coverage=0.98, leakage_risk="low")
        report = generate_report(None, None, audit, None)

        assert "IC (Pearson): 0.06" in report
        assert "Rank IC (Spearman): 0.07" in report
        assert "Coverage: 0.98" in report
        assert "Leakage risk: low" in report

    def test_experiment_setup(self):
        exp = _make_experiment(
            experiment_id="exp-042",
            split_method="k_fold",
            parameters={"n_folds": 5},
            status="completed",
            created_by="ai",
        )
        report = generate_report(exp, None, None, None)

        assert "Experiment ID: exp-042" in report
        assert "Split method: k_fold" in report
        assert "completed" in report
        assert "ai" in report

    def test_results_table(self):
        bt = _make_backtest_result(
            metrics=dict(
                annual_return=0.12,
                volatility=0.15,
                sharpe=0.8,
                max_drawdown=-0.10,
                turnover=0.5,
                win_rate=0.55,
                excess_return=0.08,
                information_ratio=0.6,
            )
        )
        report = generate_report(None, None, None, bt)

        assert "| Metric | Value |" in report
        assert "| Annual Return | 0.1200 |" in report
        assert "| Sharpe Ratio | 0.8000 |" in report
        assert "| Max Drawdown | -0.1000 |" in report

    def test_risk_review_checklist(self):
        report = generate_report(None, None, None, None)

        assert "Governance checklist:" in report
        assert "Look-ahead bias" in report
        assert "Survivorship bias" in report
        assert "Transaction costs" in report
        assert "Overfitting risk" in report
        assert "Regime dependency" in report
        assert "Sample size" in report

    def test_risk_review_leakage_when_present(self):
        audit = _make_audit_result(leakage_risk="medium")
        report = generate_report(None, None, audit, None)
        assert "Leakage risk assessment: **medium**" in report

    def test_next_experiments_section(self):
        report = generate_report(None, None, None, None)
        assert "Walk-forward validation" in report
        assert "Multi-factor combination" in report
        assert "Transaction cost sensitivity" in report


class TestArtifactLinks:
    """Verify artifact links are present when data is provided."""

    def test_experiment_artifact_link(self):
        exp = _make_experiment(experiment_id="exp-099")
        report = generate_report(exp, None, None, None)
        assert "`experiments/exp-099.yaml`" in report

    def test_factor_spec_artifact_link(self):
        spec = _make_factor_spec(factor_id="fct-077")
        report = generate_report(None, spec, None, None)
        assert "`factors/fct-077.yaml`" in report

    def test_no_artifact_links_when_none(self):
        report = generate_report(None, None, None, None)
        assert "experiments/" not in report
        assert "factors/" not in report


class TestConclusionVerdict:
    """Verify conclusion verdict is one of the four expected values."""

    @pytest.mark.parametrize("audit_kw,bt_kw,expected", [
        # Promising: high IC + high sharpe
        ({"rank_ic": 0.10}, {"metrics": {"sharpe": 1.2}}, "promising"),
        # Weak: moderate IC or positive sharpe
        ({"rank_ic": 0.03}, {"metrics": {"sharpe": 0.1}}, "weak"),
        ({"rank_ic": 0.01}, {"metrics": {"sharpe": 0.5}}, "weak"),
        # Rejected: very low IC and negative sharpe
        ({"rank_ic": 0.005}, {"metrics": {"sharpe": -0.5}}, "rejected"),
        # Inconclusive: borderline values
        ({"rank_ic": 0.015}, {"metrics": {"sharpe": -0.1}}, "inconclusive"),
    ])
    def test_verdict_values(self, audit_kw, bt_kw, expected):
        audit = _make_audit_result(**audit_kw)
        bt = _make_backtest_result(**bt_kw)
        verdict = _determine_verdict(audit, bt)
        assert verdict == expected

    def test_verdict_inconclusive_with_none_audit(self):
        assert _determine_verdict(None, None) == "inconclusive"

    def test_verdict_inconclusive_with_none_backtest(self):
        audit = _make_audit_result()
        assert _determine_verdict(audit, None) == "inconclusive"

    def test_verdict_is_one_of_four(self):
        """All possible inputs produce one of the four verdicts."""
        valid_verdicts = {"promising", "weak", "rejected", "inconclusive"}
        for ic in [0.0, 0.01, 0.03, 0.06, 0.1]:
            for sharpe in [-1.0, -0.1, 0.0, 0.3, 1.0]:
                audit = _make_audit_result(rank_ic=ic)
                bt = _make_backtest_result(metrics={"sharpe": sharpe})
                verdict = _determine_verdict(audit, bt)
                assert verdict in valid_verdicts, f"Unexpected verdict: {verdict}"
