"""Markdown research report generator for SYNAPSE experiments."""

from __future__ import annotations

from synapse.experiment.record import ExperimentRecord
from synapse.factor.spec import FactorSpec
from synapse.factor.audit import FactorAuditResult
from synapse.backtest.engine import BacktestResult


def generate_report(
    experiment: ExperimentRecord | None,
    factor_spec: FactorSpec | None,
    audit_result: FactorAuditResult | None,
    backtest_result: BacktestResult | None,
) -> str:
    """Generate a markdown research report from experiment artifacts.

    Report includes 10 sections per contract:
    title, hypothesis, data, factor definition, validation method,
    experiment setup, results, risk review, conclusion, next experiments.
    """
    sections = []

    # 1. Title
    title = experiment.name if experiment else "Untitled Research"
    sections.append(f"# {title}\n")

    # 2. Hypothesis
    sections.append("## Hypothesis\n")
    if factor_spec:
        sections.append(
            f"This research tests whether **{factor_spec.name}** ({factor_spec.factor_id}) "
            f"has predictive power for {factor_spec.domain} returns.\n"
        )
        sections.append(f"- Formula: `{factor_spec.formula}`")
        sections.append(f"- Expected direction: {factor_spec.direction}")
        sections.append(f"- Universe: {factor_spec.universe}\n")
    else:
        sections.append("No factor specification provided.\n")

    # 3. Data
    sections.append("## Data\n")
    if experiment:
        sections.append(f"- Data version: {experiment.data_version}")
        sections.append(f"- Factor version: {experiment.factor_version}")
    else:
        sections.append("No experiment data available.\n")
    sections.append("")

    # 4. Factor Definition
    sections.append("## Factor Definition\n")
    if factor_spec:
        sections.append("| Field | Value |")
        sections.append("|-------|-------|")
        sections.append(f"| Factor ID | {factor_spec.factor_id} |")
        sections.append(f"| Name | {factor_spec.name} |")
        sections.append(f"| Formula | `{factor_spec.formula}` |")
        sections.append(f"| Frequency | {factor_spec.frequency} |")
        sections.append(f"| Direction | {factor_spec.direction} |")
        sections.append(f"| Created by | {factor_spec.created_by} |")
        sections.append(f"| Version | {factor_spec.version} |\n")
    else:
        sections.append("No factor specification provided.\n")

    # 5. Validation Method
    sections.append("## Validation Method\n")
    if audit_result:
        sections.append("Factor audit metrics computed against forward returns:\n")
        sections.append(f"- IC (Pearson): {audit_result.ic}")
        sections.append(f"- Rank IC (Spearman): {audit_result.rank_ic}")
        sections.append(f"- Coverage: {audit_result.coverage}")
        sections.append(f"- Leakage risk: {audit_result.leakage_risk}\n")
    else:
        sections.append("No audit results available.\n")

    # 6. Experiment Setup
    sections.append("## Experiment Setup\n")
    if experiment:
        sections.append(f"- Experiment ID: {experiment.experiment_id}")
        sections.append(f"- Split method: {experiment.split_method or 'N/A'}")
        sections.append(f"- Parameters: {experiment.parameters}")
        sections.append(f"- Status: {experiment.status}")
        sections.append(f"- Created by: {experiment.created_by}\n")
    else:
        sections.append("No experiment setup available.\n")

    # 7. Results
    sections.append("## Results\n")
    if backtest_result and backtest_result.metrics:
        m = backtest_result.metrics
        sections.append("| Metric | Value |")
        sections.append("|--------|-------|")
        sections.append(f"| Annual Return | {m.annual_return:.4f} |")
        sections.append(f"| Volatility | {m.volatility:.4f} |")
        sections.append(f"| Sharpe Ratio | {m.sharpe:.4f} |")
        sections.append(f"| Max Drawdown | {m.max_drawdown:.4f} |")
        sections.append(f"| Turnover | {m.turnover:.4f} |")
        sections.append(f"| Win Rate | {m.win_rate:.4f} |")
        sections.append(f"| Excess Return | {m.excess_return:.4f} |")
        sections.append(f"| Information Ratio | {m.information_ratio:.4f} |\n")
    else:
        sections.append("No backtest results available.\n")

    # 8. Risk Review
    sections.append("## Risk Review\n")
    sections.append("Governance checklist:\n")
    sections.append("- [ ] Look-ahead bias: factor uses only historically available data")
    sections.append("- [ ] Survivorship bias: universe includes delisted securities")
    sections.append("- [ ] Transaction costs: explicitly modeled (see config)")
    sections.append("- [ ] Overfitting risk: out-of-sample validation performed")
    sections.append("- [ ] Regime dependency: tested across market conditions")
    sections.append(
        "- [ ] Sample size: sufficient data points for statistical significance\n"
    )
    if audit_result:
        sections.append(
            f"- Leakage risk assessment: **{audit_result.leakage_risk}**\n"
        )

    # 9. Conclusion
    sections.append("## Conclusion\n")
    verdict = _determine_verdict(audit_result, backtest_result)
    sections.append(f"**Conclusion: {verdict}**\n")
    sections.append("Evidence:")
    if audit_result:
        sections.append(
            f"- IC: {audit_result.ic}, Rank IC: {audit_result.rank_ic}"
        )
    if backtest_result and backtest_result.metrics:
        sections.append(
            f"- Sharpe: {backtest_result.metrics.sharpe}, "
            f"Max DD: {backtest_result.metrics.max_drawdown}"
        )
    sections.append("\nRisks:")
    if audit_result and audit_result.leakage_risk in ("medium", "high"):
        sections.append(f"- Elevated leakage risk ({audit_result.leakage_risk})")
    sections.append("- Single-period backtest, not walk-forward validated")
    sections.append("\nNext steps:")
    sections.append("- Expand universe and time period")
    sections.append("- Walk-forward validation")
    sections.append("- Cross-asset correlation analysis")
    sections.append("\nHuman review required: yes\n")

    # 10. Next Experiments
    sections.append("## Next Experiments\n")
    sections.append("1. Walk-forward validation with expanding window")
    sections.append("2. Multi-factor combination (momentum + value)")
    sections.append("3. Different rebalance frequencies (weekly vs monthly)")
    sections.append("4. Transaction cost sensitivity analysis\n")

    # Artifact links
    sections.append("---\n")
    sections.append("## Artifacts\n")
    if experiment:
        sections.append(
            f"- Experiment record: `experiments/{experiment.experiment_id}.yaml`"
        )
    if factor_spec:
        sections.append(
            f"- Factor spec: `factors/{factor_spec.factor_id}.yaml`"
        )
    sections.append("- Report generated by SYNAPSE research pipeline\n")

    return "\n".join(sections)


def _determine_verdict(
    audit_result: FactorAuditResult | None,
    backtest_result: BacktestResult | None,
) -> str:
    """Determine conclusion verdict from results."""
    if not audit_result or not backtest_result:
        return "inconclusive"

    ic = abs(audit_result.rank_ic)
    sharpe = backtest_result.metrics.sharpe if backtest_result.metrics else 0

    if ic > 0.05 and sharpe > 0.5:
        return "promising"
    elif ic > 0.02 or sharpe > 0:
        return "weak"
    elif ic < 0.01 and sharpe < 0:
        return "rejected"
    else:
        return "inconclusive"
