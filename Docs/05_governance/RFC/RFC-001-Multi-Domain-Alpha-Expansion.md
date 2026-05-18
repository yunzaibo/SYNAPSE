# RFC-001 Multi-domain Alpha Expansion

## Status

Draft

## Problem

SYNAPSE may eventually support multiple alpha domains.

Potential domains:

- Cross-sectional equity factors
- Event-driven research
- Time-series forecasting
- Futures CTA
- Crypto research
- Alternative data

## Proposal

Do not build all domains in P0.

Use a domain-pack architecture:

```txt
Research OS Core
├─ Common data / experiment / report / governance layer
└─ Alpha Domain Packs
   ├─ Equity Factors
   ├─ Event-driven
   ├─ Time-series
   └─ Crypto
```

## Open Questions

- What should be common across all domains?
- What should be domain-specific?
- How should domain packs register validation methods?
- How should agents behave differently across domains?
