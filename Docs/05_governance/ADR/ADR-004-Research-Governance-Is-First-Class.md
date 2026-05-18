# ADR-004 Research Governance Is First-class

## Status

Accepted

## Context

Quant research is vulnerable to false positives and overfitting.

Common risks include:

- Look-ahead bias
- Survivorship bias
- Data leakage
- Overfitting
- Hidden parameter search
- Ignored transaction costs
- Regime-specific performance
- Unrecorded failed experiments

## Decision

Research governance is a first-class system layer.

It should not be implemented as a later plugin.

## Required Governance Concepts

- Time-aware data metadata
- Purging / embargoing
- Walk-forward validation
- CPCV when applicable
- IC / RankIC
- Mutual information
- SHAP consistency
- Experiment lineage
- Backtest assumption recording
- Risk review before report finalization

## Consequences

Positive:

- Higher trust
- Better reproducibility
- Stronger interview/project credibility

Negative:

- More upfront engineering
- More schema and artifact design
