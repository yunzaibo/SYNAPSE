"""SYNAPSE Analytics -- Pattern detection, behavioral stats, evolution, and bias analysis.

Uses lazy imports to avoid circular dependency with synapse.core.schemas.signal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from synapse.analytics.error_pattern import (
        ErrorPatternAnalyzer,
        ErrorPatternReport,
        TrendDirection,
    )
    from synapse.analytics.behavioral import (
        BehavioralStatsAnalyzer,
        BehavioralStatsReport,
    )
    from synapse.analytics.evolution import (
        ThesisEvolutionAnalyzer,
        EvolutionReport,
    )
    from synapse.analytics.bias import (
        BiasDetector,
        BiasReport,
    )
    from synapse.analytics.drift import (
        DriftDetector,
        DriftReport,
    )
    from synapse.analytics.correlation import (
        CorrelationAnalyzer,
        CorrelationReport,
    )

__all__ = [
    # Error Pattern
    "ErrorPatternAnalyzer",
    "ErrorPatternReport",
    "TrendDirection",
    # Behavioral Stats
    "BehavioralStatsAnalyzer",
    "BehavioralStatsReport",
    # Evolution
    "ThesisEvolutionAnalyzer",
    "EvolutionReport",
    # Bias
    "BiasDetector",
    "BiasReport",
    # Drift
    "DriftDetector",
    "DriftReport",
    # Correlation
    "CorrelationAnalyzer",
    "CorrelationReport",
]


def __getattr__(name: str):
    """Lazy import to avoid circular dependency."""
    if name in __all__:
        if name in ("ErrorPatternAnalyzer", "ErrorPatternReport", "TrendDirection"):
            from synapse.analytics.error_pattern import (
                ErrorPatternAnalyzer,
                ErrorPatternReport,
                TrendDirection,
            )
            _map = {
                "ErrorPatternAnalyzer": ErrorPatternAnalyzer,
                "ErrorPatternReport": ErrorPatternReport,
                "TrendDirection": TrendDirection,
            }
        elif name in ("BehavioralStatsAnalyzer", "BehavioralStatsReport"):
            from synapse.analytics.behavioral import (
                BehavioralStatsAnalyzer,
                BehavioralStatsReport,
            )
            _map = {
                "BehavioralStatsAnalyzer": BehavioralStatsAnalyzer,
                "BehavioralStatsReport": BehavioralStatsReport,
            }
        elif name in ("ThesisEvolutionAnalyzer", "EvolutionReport"):
            from synapse.analytics.evolution import (
                ThesisEvolutionAnalyzer,
                EvolutionReport,
            )
            _map = {
                "ThesisEvolutionAnalyzer": ThesisEvolutionAnalyzer,
                "EvolutionReport": EvolutionReport,
            }
        elif name in ("BiasDetector", "BiasReport"):
            from synapse.analytics.bias import BiasDetector, BiasReport
            _map = {
                "BiasDetector": BiasDetector,
                "BiasReport": BiasReport,
            }
        elif name in ("DriftDetector", "DriftReport"):
            from synapse.analytics.drift import DriftDetector, DriftReport
            _map = {
                "DriftDetector": DriftDetector,
                "DriftReport": DriftReport,
            }
        elif name in ("CorrelationAnalyzer", "CorrelationReport"):
            from synapse.analytics.correlation import (
                CorrelationAnalyzer,
                CorrelationReport,
            )
            _map = {
                "CorrelationAnalyzer": CorrelationAnalyzer,
                "CorrelationReport": CorrelationReport,
            }
        else:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        return _map[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
