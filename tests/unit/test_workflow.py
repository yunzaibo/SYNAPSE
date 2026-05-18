"""Tests for Research Workflow (TASK-007)."""

import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from synapse.core.activity import ActivityLog, ActivityType
from synapse.core.schemas.base import MarketContext
from synapse.core.schemas.decision import (
    Decision,
    DecisionType,
    TimeHorizon,
    AttentionOrigin,
)
from synapse.core.schemas.event import Event, EventType, ImpactLevel
from synapse.core.schemas.position import (
    Position,
    ResearchState,
    ThesisStatus,
    AttentionState,
)
from synapse.core.schemas.review import Review, ReviewOutcome
from synapse.core.schemas.signal import (
    Signal,
    SignalType as SigSignalType,
    SignalStrength as SigStrength,
)
from synapse.core.schemas.watchlist import WatchlistEntry, TriggerType
from synapse.core.temporal import CST

from synapse.core.workflow.daily_research import run_daily_research, DailyResearchResult
from synapse.core.workflow.decision_flow import record_decision
from synapse.core.workflow.review_flow import submit_review


# --- Test Helpers ---


def _make_event(
    event_id: str = "evt_test01",
    title: str = "测试事件",
    event_date: date | None = None,
    related_tickers: list[str] | None = None,
) -> Event:
    return Event(
        id=event_id,
        event_type=EventType.EARNINGS,
        title=title,
        description="测试事件描述",
        event_date=event_date or date(2026, 5, 18),
        related_tickers=related_tickers or ["600519"],
        impact_level=ImpactLevel.HIGH,
    )


def _make_signal(
    signal_id: str = "sig_test01",
    signal_type: SigSignalType = SigSignalType.ATTENTION_SPIKE,
    strength: SigStrength = SigStrength.STRONG,
    related_tickers: list[str] | None = None,
) -> Signal:
    return Signal(
        id=signal_id,
        signal_type=signal_type,
        strength=strength,
        description="测试信号",
        related_tickers=related_tickers or ["600519"],
    )


def _make_position(
    pos_id: str = "pos_test01",
    ticker: str = "600519",
    thesis_status: ThesisStatus = ThesisStatus.ACTIVE,
) -> Position:
    return Position(
        id=pos_id,
        ticker=ticker,
        symbol="贵州茅台",
        market="CN_A",
        thesis_at_entry="测试 thesis",
        research_state=ResearchState(thesis_status=thesis_status),
    )


def _make_decision(
    decision_id: str = "dec_test01",
    ticker: str = "600519",
    symbol: str = "贵州茅台",
    decision_type: DecisionType = DecisionType.BUY,
    thesis: str = "测试 thesis",
    linked_thesis_id: str = "ths_test01",
    created_at: datetime | None = None,
) -> Decision:
    return Decision(
        id=decision_id,
        ticker=ticker,
        symbol=symbol,
        market="CN_A",
        decision_type=decision_type,
        thesis=thesis,
        linked_thesis_id=linked_thesis_id,
        created_at=created_at or datetime(2026, 5, 18, 14, 0, tzinfo=CST),
    )


def _make_review(
    review_id: str = "rev_test01",
    linked_decision_id: str = "dec_test01",
    linked_thesis_id: str = "ths_test01",
    review_outcome: ReviewOutcome = ReviewOutcome.THESIS_CONFIRMED,
) -> Review:
    return Review(
        id=review_id,
        linked_decision_id=linked_decision_id,
        linked_thesis_id=linked_thesis_id,
        review_outcome=review_outcome,
        review_note="测试 review",
    )


# --- Daily Research Tests ---


class TestDailyResearch:
    def test_run_daily_research_generates_watchlist(self):
        """run_daily_research generates watchlist from events, signals, positions."""
        target_date = date(2026, 5, 18)
        events = [_make_event()]
        signals = [_make_signal()]
        positions = [_make_position()]

        result = run_daily_research(
            target_date=target_date,
            events=events,
            signals=signals,
            positions=positions,
        )

        assert isinstance(result, DailyResearchResult)
        assert result.target_date == target_date
        assert result.watchlist_count == 3  # 1 event + 1 signal + 1 position
        assert result.events_loaded == 1
        assert result.signals_loaded == 1
        assert result.positions_loaded == 1

    def test_run_daily_research_empty_inputs(self):
        """run_daily_research with no inputs produces empty watchlist."""
        result = run_daily_research(
            target_date=date(2026, 5, 18),
            events=[],
            signals=[],
            positions=[],
        )

        assert result.watchlist_count == 0

    def test_run_daily_research_logs_activity(self):
        """run_daily_research logs watchlist.generated when activity_log provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "activity.jsonl"
            activity_log = ActivityLog(log_path)

            result = run_daily_research(
                target_date=date(2026, 5, 18),
                events=[],
                signals=[],
                positions=[],
                activity_log=activity_log,
            )

            assert result.activity_logged is True
            entries = activity_log.read_all()
            assert len(entries) == 1
            assert entries[0].type == ActivityType.WATCHLIST_GENERATED.value

    def test_run_daily_research_saves_watchlist(self):
        """run_daily_research saves watchlist files when output_dir provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            events = [_make_event()]
            result = run_daily_research(
                target_date=date(2026, 5, 18),
                events=events,
                signals=[],
                positions=[],
                watchlist_output_dir=tmpdir,
            )

            watchlist_dir = Path(tmpdir) / "2026-05-18"
            assert watchlist_dir.exists()
            yaml_files = list(watchlist_dir.glob("*.yaml"))
            assert len(yaml_files) == 1

    def test_daily_research_result_to_dict(self):
        """DailyResearchResult serializes correctly."""
        result = run_daily_research(
            target_date=date(2026, 5, 18),
            events=[_make_event()],
            signals=[],
            positions=[],
        )

        d = result.to_dict()
        assert d["target_date"] == "2026-05-18"
        assert d["watchlist_count"] == 1
        assert d["events_loaded"] == 1


# --- Decision Flow Tests ---


class TestDecisionFlow:
    def test_record_decision_saves_and_rebuilds(self):
        """record_decision saves decision and rebuilds positions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            decision = _make_decision()

            result = record_decision(
                decision=decision,
                existing_decisions=[],
                workspace_dir=tmpdir,
            )

            assert result.decision.id == "dec_test01"
            assert result.position_rebuilt is True

            # Verify decision file was saved
            decision_dir = Path(tmpdir) / "decisions"
            yaml_files = list(decision_dir.rglob("meta.yaml"))
            assert len(yaml_files) == 1

    def test_record_decision_logs_activity(self):
        """record_decision logs decision.recorded when activity_log provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "activity.jsonl"
            activity_log = ActivityLog(log_path)
            decision = _make_decision()

            result = record_decision(
                decision=decision,
                existing_decisions=[],
                activity_log=activity_log,
                workspace_dir=tmpdir,
            )

            assert result.activity_logged is True
            entries = activity_log.read_all()
            assert len(entries) == 1
            assert entries[0].type == ActivityType.DECISION_RECORDED.value

    def test_record_decision_without_workspace(self):
        """record_decision works without workspace_dir (no file ops)."""
        decision = _make_decision()

        result = record_decision(
            decision=decision,
            existing_decisions=[],
        )

        assert result.decision.id == "dec_test01"
        assert result.position_rebuilt is False

    def test_record_decision_includes_in_rebuild(self):
        """New decision is included in position rebuild even if not in existing_decisions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            decision = _make_decision()

            result = record_decision(
                decision=decision,
                existing_decisions=[],
                workspace_dir=tmpdir,
            )

            # Position should be created from the new decision
            positions_dir = Path(tmpdir) / "positions" / "current"
            yaml_files = list(positions_dir.glob("*.yaml"))
            assert len(yaml_files) == 1


# --- Review Flow Tests ---


class TestReviewFlow:
    def test_submit_review_saves(self):
        """submit_review saves review to YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            review = _make_review()

            # Create a decision directory first
            decision_dir = Path(tmpdir) / "decisions" / "dec_test01"
            decision_dir.mkdir(parents=True)

            result = submit_review(
                review=review,
                workspace_dir=tmpdir,
            )

            assert result.review.id == "rev_test01"
            assert result.saved is True

            review_path = decision_dir / "review.yaml"
            assert review_path.exists()

    def test_submit_review_logs_activity(self):
        """submit_review logs review.completed when activity_log provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "activity.jsonl"
            activity_log = ActivityLog(log_path)
            review = _make_review()

            result = submit_review(
                review=review,
                activity_log=activity_log,
            )

            assert result.activity_logged is True
            entries = activity_log.read_all()
            assert len(entries) == 1
            assert entries[0].type == ActivityType.REVIEW_COMPLETED.value

    def test_submit_review_without_workspace(self):
        """submit_review works without workspace_dir (no file ops)."""
        review = _make_review()

        result = submit_review(review=review)

        assert result.review.id == "rev_test01"
        assert result.saved is False

    def test_submit_review_without_decision_link(self):
        """submit_review without linked_decision_id skips file save."""
        with tempfile.TemporaryDirectory() as tmpdir:
            review = Review(
                id="rev_nolink",
                review_outcome=ReviewOutcome.THESIS_CONFIRMED,
                review_note="无关联决策",
            )

            result = submit_review(
                review=review,
                workspace_dir=tmpdir,
            )

            assert result.saved is False
