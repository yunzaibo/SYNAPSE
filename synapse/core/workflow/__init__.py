"""Research Workflow — Orchestrate daily research, decisions, and reviews.

Workflow components:
- daily_research: run_daily_research() → DailyResearchResult
- decision_flow: record_decision() → Decision
- review_flow: submit_review() → Review
"""

from synapse.core.workflow.daily_research import run_daily_research, DailyResearchResult
from synapse.core.workflow.decision_flow import record_decision
from synapse.core.workflow.review_flow import submit_review

__all__ = [
    "run_daily_research",
    "DailyResearchResult",
    "record_decision",
    "submit_review",
]
