# Error Codes

## Categories

```txt
DATA_*
FACTOR_*
EXPERIMENT_*
BACKTEST_*
REPORT_*
AGENT_*
GOVERNANCE_*
```

## P0 Implemented Error Codes

| Code | Meaning | Module |
|---|---|---|
| DATA_MISSING_FIELD | Required data field is missing | data/validator |
| DATA_INVALID_TIME_RANGE | Time range is invalid | data/validator |
| DATA_AVAILABLE_AT_MISSING | Available-at metadata is missing | data/validator |
| FACTOR_INVALID_SPEC | Factor definition is invalid | factor/compute |
| FACTOR_COMPUTE_FAILED | Factor calculation failed | factor/compute |
| EXPERIMENT_RECORD_MISSING | Experiment record is missing | experiment/tracker |
| BACKTEST_CONFIG_INVALID | Backtest configuration is invalid | backtest/config |
| GOVERNANCE_LEAKAGE_RISK | Potential data leakage detected | factor/audit |
| AGENT_ACTION_NOT_ALLOWED | Agent attempted a forbidden action | experiment/tracker |
| REPORT_ARTIFACT_MISSING | Report cannot find required artifact | report/generator |

Source: `synapse/core/errors.py`

## Usage

```python
from synapse.core.errors import DATA_MISSING_FIELD, AGENT_ACTION_NOT_ALLOWED

raise DATA_MISSING_FIELD("close column is required")
raise AGENT_ACTION_NOT_ALLOWED("Experiments cannot be deleted per governance policy")
```
