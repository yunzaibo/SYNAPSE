# Report Contract

## Purpose

Define research report structure and traceability requirements.

## Report Sections (P0 Implemented)

A research report must include:

1. Title
2. Hypothesis
3. Data
4. Factor Definition
5. Validation Method
6. Experiment Setup
7. Results
8. Risk Review
9. Conclusion
10. Next Experiments

Source: `synapse/report/generator.py`

## Conclusion Format

```
Conclusion: promising / weak / rejected / inconclusive
Evidence:
Risks:
Next steps:
Human review required: yes
```

## Risk Review Checklist

- [ ] Look-ahead bias
- [ ] Survivorship bias
- [ ] Transaction costs
- [ ] Overfitting risk
- [ ] Regime dependency
- [ ] Sample size

## Rule

A report must be traceable to experiment artifacts.

## API

```python
from synapse.report.generator import generate_report

report = generate_report(experiment, factor_spec, audit_result, backtest_result)
# Returns markdown string with all 10 sections
```
