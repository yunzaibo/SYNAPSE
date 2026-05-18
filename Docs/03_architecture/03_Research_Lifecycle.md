# Research Lifecycle

## Overview

SYNAPSE research lifecycle:

```txt
Idea
→ Research Plan
→ Data Spec
→ Factor Spec
→ Factor Audit
→ Experiment
→ Backtest
→ Risk Review
→ Report
→ Research Memory
```

## 1. Idea

An idea is a natural language hypothesis.

Example:

```txt
High dividend yield combined with low volatility may produce stable excess return in large-cap equities.
```

## 2. Research Plan

A structured plan includes hypothesis, universe, time range, data fields, factor definition, validation method, backtest method, and expected risks.

## 3. Data Spec

Data spec records dataset name, source, frequency, time range, available-at assumptions, adjustments, and missing value rules.

## 4. Factor Spec

Factor spec records factor name, formula or code, input fields, frequency, direction, expected relationship to return, and known risks.

## 5. Factor Audit

Audit checks coverage, missing rate, distribution, outliers, correlation with existing factors, IC / RankIC, MI if applicable, leakage risk, and stability.

## 6. Experiment

Experiment records data version, factor version, model version, parameters, split strategy, run time, and artifacts.

## 7. Backtest

Backtest records universe, benchmark, rebalancing frequency, transaction cost, slippage, position constraints, and performance metrics.

## 8. Risk Review

Risk review checks look-ahead bias, survivorship bias, overfitting, cost assumptions, turnover, regime dependency, sample size, and hidden parameter tuning.

## 9. Report

Report contains hypothesis, method, data, results, risks, conclusion, and next experiments.

## 10. Research Memory

Research memory stores accepted ideas, failed ideas, risk patterns, factor relationships, experiment summaries, and open questions.
