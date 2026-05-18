class SynapseError(Exception):
    """Base class for all SYNAPSE errors."""
    code = "SYNAPSE_ERROR"
    default_message = "An error occurred in SYNAPSE"

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(f"[{self.code}] {self.message}")


class DATA_MISSING_FIELD(SynapseError):
    code = "DATA_MISSING_FIELD"
    default_message = "Required data field is missing"


class DATA_INVALID_TIME_RANGE(SynapseError):
    code = "DATA_INVALID_TIME_RANGE"
    default_message = "Time range is invalid"


class DATA_AVAILABLE_AT_MISSING(SynapseError):
    code = "DATA_AVAILABLE_AT_MISSING"
    default_message = "Available-at metadata is missing"


class FACTOR_INVALID_SPEC(SynapseError):
    code = "FACTOR_INVALID_SPEC"
    default_message = "Factor definition is invalid"


class FACTOR_COMPUTE_FAILED(SynapseError):
    code = "FACTOR_COMPUTE_FAILED"
    default_message = "Factor calculation failed"


class EXPERIMENT_RECORD_MISSING(SynapseError):
    code = "EXPERIMENT_RECORD_MISSING"
    default_message = "Experiment record is missing"


class BACKTEST_CONFIG_INVALID(SynapseError):
    code = "BACKTEST_CONFIG_INVALID"
    default_message = "Backtest configuration is invalid"


class GOVERNANCE_LEAKAGE_RISK(SynapseError):
    code = "GOVERNANCE_LEAKAGE_RISK"
    default_message = "Potential data leakage detected"


class AGENT_ACTION_NOT_ALLOWED(SynapseError):
    code = "AGENT_ACTION_NOT_ALLOWED"
    default_message = "Agent attempted a forbidden action"


class REPORT_ARTIFACT_MISSING(SynapseError):
    code = "REPORT_ARTIFACT_MISSING"
    default_message = "Report cannot find required artifact"
