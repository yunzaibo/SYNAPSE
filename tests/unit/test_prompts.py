"""Tests for synapse.agent.prompts prompt templates."""

from synapse.agent.prompts import (
    SYSTEM_INSTRUCTION,
    draft_research_plan,
    explain_results,
    draft_report,
    generate_risk_checklist,
)
from synapse.experiment.record import ExperimentRecord
from synapse.factor.spec import FactorSpec
from synapse.factor.audit import FactorAuditResult
from synapse.backtest.engine import BacktestResult
from synapse.backtest.config import BacktestConfig
from synapse.backtest.metrics import BacktestMetrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_experiment() -> ExperimentRecord:
    return ExperimentRecord(
        experiment_id="EXP-001",
        name="Momentum Factor Test",
        research_task_id="RT-001",
        data_version="1.0",
        factor_version="1.0",
        model_version="1.0",
        split_method="time_series",
        parameters={"window": 20},
        status="succeeded",
    )


def _make_factor_spec() -> FactorSpec:
    return FactorSpec(
        factor_id="FAC-001",
        name="Momentum",
        description="20-day price momentum",
        domain="cross_sectional_equity",
        inputs=["close"],
        formula="close / close.shift(20) - 1",
        frequency="daily",
        direction="positive",
        universe="CSI300",
        created_by="human",
    )


def _make_audit_result() -> FactorAuditResult:
    return FactorAuditResult(
        factor_id="FAC-001",
        version="1.0",
        coverage=0.95,
        missing_rate=0.05,
        ic=0.03,
        rank_ic=0.04,
        leakage_risk="low",
    )


def _make_backtest_config() -> BacktestConfig:
    return BacktestConfig(
        universe="CSI300",
        benchmark="000300.SH",
        start_date="2020-01-01",
        end_date="2023-12-31",
        rebalance_frequency="monthly",
        transaction_cost_bps=10.0,
        slippage_bps=5.0,
    )


def _make_backtest_result() -> BacktestResult:
    return BacktestResult(
        config=_make_backtest_config(),
        metrics=BacktestMetrics(
            annual_return=0.12,
            volatility=0.15,
            sharpe=0.8,
            max_drawdown=-0.10,
            turnover=0.05,
            win_rate=0.55,
            excess_return=0.08,
            information_ratio=0.6,
        ),
        status="succeeded",
    )


# ---------------------------------------------------------------------------
# Tests: draft_research_plan
# ---------------------------------------------------------------------------

class TestDraftResearchPlan:
    def test_returns_nonempty_string(self):
        result = draft_research_plan("Momentum predicts returns")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_system_instruction(self):
        result = draft_research_plan("test hypothesis")
        assert "must not execute trades" in result
        assert "modify experiment records" in result

    def test_contains_created_by_ai(self):
        result = draft_research_plan("test hypothesis")
        assert "created_by" in result
        assert "ai" in result

    def test_includes_hypothesis_text(self):
        hypothesis = "Price momentum predicts future returns in equity markets"
        result = draft_research_plan(hypothesis)
        assert hypothesis in result

    def test_includes_required_sections(self):
        result = draft_research_plan("hypothesis")
        assert "Data Requirements" in result
        assert "Factor Definition" in result
        assert "Validation Approach" in result
        assert "Backtest Setup" in result
        assert "Risk Review" in result


# ---------------------------------------------------------------------------
# Tests: explain_results
# ---------------------------------------------------------------------------

class TestExplainResults:
    def test_returns_nonempty_string(self):
        result = explain_results(_make_experiment(), _make_audit_result(), _make_backtest_result())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_system_instruction(self):
        result = explain_results(None, None, None)
        assert "must not execute trades" in result
        assert "modify experiment records" in result

    def test_contains_created_by_ai(self):
        result = explain_results(None, None, None)
        assert "created_by" in result
        assert "ai" in result

    def test_includes_experiment_info(self):
        exp = _make_experiment()
        result = explain_results(exp, None, None)
        assert exp.experiment_id in result
        assert exp.status in result

    def test_includes_audit_info(self):
        audit = _make_audit_result()
        result = explain_results(None, audit, None)
        assert str(audit.ic) in result
        assert str(audit.rank_ic) in result
        assert str(audit.coverage) in result

    def test_includes_backtest_info(self):
        bt = _make_backtest_result()
        result = explain_results(None, None, bt)
        assert str(bt.metrics.sharpe) in result
        assert str(bt.metrics.max_drawdown) in result
        assert str(bt.metrics.annual_return) in result
        assert str(bt.metrics.win_rate) in result

    def test_handles_none_inputs(self):
        result = explain_results(None, None, None)
        assert "Experiment:" not in result
        assert "Factor Audit:" not in result
        assert "Backtest:" not in result
        # Still has structure
        assert "# Results Explanation" in result

    def test_handles_partial_inputs(self):
        exp = _make_experiment()
        result = explain_results(exp, None, None)
        assert exp.experiment_id in result
        assert "Factor Audit:" not in result
        assert "Backtest:" not in result

    def test_requires_human_review(self):
        result = explain_results(None, None, None)
        assert "requires_human_review: true" in result


# ---------------------------------------------------------------------------
# Tests: draft_report
# ---------------------------------------------------------------------------

class TestDraftReport:
    def test_returns_nonempty_string(self):
        result = draft_report(_make_factor_spec(), _make_audit_result(), _make_backtest_result())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_system_instruction(self):
        result = draft_report(None, None, None)
        assert "must not execute trades" in result
        assert "modify experiment records" in result

    def test_contains_created_by_ai(self):
        result = draft_report(None, None, None)
        assert "created_by" in result
        assert "ai" in result

    def test_includes_factor_spec_info(self):
        fs = _make_factor_spec()
        result = draft_report(fs, None, None)
        assert fs.name in result
        assert fs.factor_id in result
        assert fs.formula in result
        assert fs.direction in result

    def test_handles_none_factor_spec(self):
        result = draft_report(None, None, None)
        assert "No factor specification provided" in result

    def test_indicates_data_availability(self):
        result = draft_report(None, _make_audit_result(), _make_backtest_result())
        assert "Audit result: Available" in result
        assert "Backtest result: Available" in result

    def test_indicates_data_unavailability(self):
        result = draft_report(None, None, None)
        assert "Audit result: Not available" in result
        assert "Backtest result: Not available" in result

    def test_includes_governance_requirements(self):
        result = draft_report(None, None, None)
        assert "look-ahead bias" in result
        assert "survivorship bias" in result
        assert "transaction costs" in result
        assert "overfitting" in result
        assert "regime dependency" in result
        assert "sample size" in result


# ---------------------------------------------------------------------------
# Tests: generate_risk_checklist
# ---------------------------------------------------------------------------

class TestGenerateRiskChecklist:
    def test_returns_nonempty_string(self):
        result = generate_risk_checklist(_make_experiment())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_system_instruction(self):
        result = generate_risk_checklist(None)
        assert "must not execute trades" in result
        assert "modify experiment records" in result

    def test_contains_created_by_ai(self):
        result = generate_risk_checklist(None)
        assert "created_by" in result
        assert "ai" in result

    def test_includes_experiment_context(self):
        exp = _make_experiment()
        result = generate_risk_checklist(exp)
        assert exp.experiment_id in result
        assert exp.name in result

    def test_handles_none_experiment(self):
        result = generate_risk_checklist(None)
        assert "No experiment context provided" in result

    def test_includes_data_integrity_category(self):
        result = generate_risk_checklist(None)
        assert "Data Integrity" in result
        assert "Look-ahead bias" in result
        assert "Survivorship bias" in result

    def test_includes_methodology_category(self):
        result = generate_risk_checklist(None)
        assert "Methodology" in result
        assert "Transaction costs" in result
        assert "Overfitting risk" in result
        assert "Sample size" in result

    def test_includes_market_regime_category(self):
        result = generate_risk_checklist(None)
        assert "Market Regime" in result
        assert "Regime dependency" in result
        assert "Crowding risk" in result
        assert "Decay risk" in result

    def test_includes_governance_category(self):
        result = generate_risk_checklist(None)
        assert "Governance" in result
        assert "Failed experiments preserved" in result
        assert "created_by: ai" in result

    def test_requires_human_review(self):
        result = generate_risk_checklist(None)
        assert "requires_human_review: true" in result

    def test_includes_output_format(self):
        result = generate_risk_checklist(None)
        assert "PASS / FAIL / UNKNOWN" in result
        assert "Risk level: low / medium / high" in result
