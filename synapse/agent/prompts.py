"""Prompt templates for AI research assistant.

All templates respect agent boundary: no trade execution, no silent
modification, no governance bypass. Every output includes created_by: ai.
"""

from __future__ import annotations

from synapse.experiment.record import ExperimentRecord
from synapse.factor.spec import FactorSpec
from synapse.factor.audit import FactorAuditResult
from synapse.backtest.engine import BacktestResult


SYSTEM_INSTRUCTION = (
    "You are a research assistant. You must not execute trades, "
    "modify experiment records, or bypass governance checks. "
    "All outputs should include metadata: created_by: ai"
)


def draft_research_plan(hypothesis: str) -> str:
    """Draft a structured research plan from a hypothesis."""
    return f"""{SYSTEM_INSTRUCTION}

# Research Plan Draft

## Hypothesis
{hypothesis}

## Required Sections
1. **Data Requirements**: Specify required data fields, time range, and universe
2. **Factor Definition**: Define the factor formula and expected direction
3. **Validation Approach**: Describe IC/RankIC testing, coverage checks, leakage risk assessment
4. **Backtest Setup**: Specify transaction costs, rebalance frequency, position limits
5. **Risk Review**: Identify potential biases and governance checkpoints

## Constraints
- All assumptions must be explicit
- Transaction costs cannot be silently omitted
- Failed experiments must be preserved
- This plan is created_by: ai and requires human review before execution
"""


def explain_results(
    experiment_record: ExperimentRecord | None,
    audit_result: FactorAuditResult | None,
    backtest_result: BacktestResult | None,
) -> str:
    """Explain backtest results in plain language."""
    exp_info = ""
    if experiment_record:
        exp_info = f"Experiment: {experiment_record.experiment_id} ({experiment_record.status})"

    audit_info = ""
    if audit_result:
        audit_info = (
            f"Factor Audit: IC={audit_result.ic}, RankIC={audit_result.rank_ic}, "
            f"Coverage={audit_result.coverage}, Leakage Risk={audit_result.leakage_risk}"
        )

    bt_info = ""
    if backtest_result and backtest_result.metrics:
        m = backtest_result.metrics
        bt_info = (
            f"Backtest: Sharpe={m.sharpe}, MaxDD={m.max_drawdown}, "
            f"Annual Return={m.annual_return}, Win Rate={m.win_rate}"
        )

    return f"""{SYSTEM_INSTRUCTION}

# Results Explanation

## Context
{exp_info}
{audit_info}
{bt_info}

## Analysis Request
Please explain these results in plain language:
1. What does the factor performance indicate?
2. Is the Sharpe ratio acceptable for this strategy type?
3. What are the main risks revealed by max drawdown and win rate?
4. Should this factor proceed to further validation?

## Metadata
created_by: ai
requires_human_review: true
"""


def draft_report(
    factor_spec: FactorSpec | None,
    audit_result: FactorAuditResult | None,
    backtest_result: BacktestResult | None,
) -> str:
    """Draft a research report outline from factor and backtest data."""
    factor_info = ""
    if factor_spec:
        factor_info = (
            f"Factor: {factor_spec.name} ({factor_spec.factor_id})\n"
            f"Formula: {factor_spec.formula}\n"
            f"Direction: {factor_spec.direction}"
        )

    return f"""{SYSTEM_INSTRUCTION}

# Report Draft Request

## Factor Information
{factor_info or "No factor specification provided"}

## Available Data
- Audit result: {"Available" if audit_result else "Not available"}
- Backtest result: {"Available" if backtest_result else "Not available"}

## Required Report Sections
Draft a markdown report with these 10 sections:
1. Title
2. Hypothesis
3. Data
4. Factor Definition
5. Validation Method
6. Experiment Setup
7. Results
8. Risk Review
9. Conclusion (use format: promising/weak/rejected/inconclusive with evidence, risks, next steps)
10. Next Experiments

## Governance Requirements
- All artifact links must use relative paths
- Conclusion must include "Human review required: yes"
- Risk review must cover: look-ahead bias, survivorship bias, transaction costs, overfitting, regime dependency, sample size

## Metadata
created_by: ai
"""


def generate_risk_checklist(experiment_record: ExperimentRecord | None) -> str:
    """Generate a risk review checklist for an experiment."""
    exp_info = ""
    if experiment_record:
        exp_info = f"Experiment: {experiment_record.experiment_id} ({experiment_record.name})"

    return f"""{SYSTEM_INSTRUCTION}

# Risk Review Checklist

## Experiment Context
{exp_info or "No experiment context provided"}

## Checklist
Evaluate each item and mark as PASS/FAIL/UNKNOWN:

### Data Integrity
- [ ] Look-ahead bias: factor uses only data available at evaluation time
- [ ] Survivorship bias: universe includes delisted securities
- [ ] Data quality: no missing values silently filled

### Methodology
- [ ] Transaction costs: explicitly modeled (not assumed zero)
- [ ] Slippage: accounted for in backtest
- [ ] Overfitting risk: out-of-sample validation performed
- [ ] Sample size: sufficient for statistical significance (n > 30)

### Market Regime
- [ ] Regime dependency: tested across bull/bear/sideways markets
- [ ] Crowding risk: factor not overly crowded
- [ ] Decay risk: factor alpha has not significantly decayed

### Governance
- [ ] Experiment record complete with all required fields
- [ ] Failed experiments preserved (not deleted)
- [ ] Parameter changes created new experiment records
- [ ] AI-generated changes marked with created_by: ai

## Output Format
For each item, provide:
- Status: PASS / FAIL / UNKNOWN
- Evidence: brief justification
- Risk level: low / medium / high

## Metadata
created_by: ai
requires_human_review: true
"""
