# ADR-002 Initial Alpha Domain: Cross-sectional Equity Factors

## Status

Accepted

## Context

SYNAPSE cannot support every alpha type at the beginning.

Alpha types differ across data, validation, modeling, execution, and risk.

## Decision

The first alpha domain is cross-sectional equity factor research.

## Rationale

This domain is suitable for P0 because:

- It has a clear research workflow
- It works well with tabular data
- It supports IC / RankIC validation
- It is easier to audit than HFT
- It fits AI-assisted research and report generation
- It avoids real-time execution complexity

## Out of Scope

- HFT
- Market making
- Real-time order book strategies
- Broker trading
- Multi-asset production portfolios
