"""Tests for TemporalContext (ADR-008)."""

from datetime import date, datetime, timezone, timedelta

import pytest

from synapse.core.temporal import TemporalContext, MarketSession, CST


class TestTemporalContext:
    """Tests for temporal semantics."""

    def _make_event_time(self, year=2026, month=5, day=18, hour=10):
        return datetime(year, month, day, hour, tzinfo=CST)

    def test_create_basic(self):
        tc = TemporalContext.create(
            event_time=self._make_event_time(),
            market_date=date(2026, 5, 18),
        )
        assert tc.event_timezone == "Asia/Shanghai"
        assert tc.market_date == date(2026, 5, 18)
        assert tc.market_session == MarketSession.NORMAL
        assert tc.created_at is not None
        assert tc.updated_at is not None

    def test_event_time_required(self):
        tc = TemporalContext(
            event_time=self._make_event_time(),
            market_date=date(2026, 5, 18),
        )
        assert tc.event_time == self._make_event_time()

    def test_market_date_required(self):
        tc = TemporalContext(
            event_time=self._make_event_time(),
            market_date=date(2026, 5, 18),
        )
        assert tc.market_date == date(2026, 5, 18)

    def test_market_session_default(self):
        tc = TemporalContext(
            event_time=self._make_event_time(),
            market_date=date(2026, 5, 18),
        )
        assert tc.market_session == MarketSession.NORMAL

    def test_event_timezone_default(self):
        tc = TemporalContext(
            event_time=self._make_event_time(),
            market_date=date(2026, 5, 18),
        )
        assert tc.event_timezone == "Asia/Shanghai"

    def test_only_asia_shanghai_p1(self):
        with pytest.raises(ValueError, match="P1 only supports"):
            TemporalContext(
                event_time=self._make_event_time(),
                event_timezone="America/New_York",
                market_date=date(2026, 5, 18),
            )

    def test_reject_naive_event_time(self):
        with pytest.raises(ValueError, match="event_time must be timezone-aware"):
            TemporalContext(
                event_time=datetime(2026, 5, 18, 10, 0),
                market_date=date(2026, 5, 18),
            )

    def test_market_session_variants(self):
        for session in MarketSession:
            tc = TemporalContext(
                event_time=self._make_event_time(),
                market_date=date(2026, 5, 18),
                market_session=session,
            )
            assert tc.market_session == session

    def test_availability_fields(self):
        now = datetime.now(CST)
        tc = TemporalContext(
            event_time=self._make_event_time(),
            market_date=date(2026, 5, 18),
            available_at=now,
            as_of_date=date(2026, 5, 17),
        )
        assert tc.available_at == now
        assert tc.as_of_date == date(2026, 5, 17)

    def test_to_dict(self):
        tc = TemporalContext.create(
            event_time=self._make_event_time(),
            market_date=date(2026, 5, 18),
        )
        d = tc.to_dict()
        assert d["event_timezone"] == "Asia/Shanghai"
        assert d["market_date"] == "2026-05-18"
        assert d["market_session"] == "normal"

    def test_to_dict_with_availability(self):
        tc = TemporalContext(
            event_time=self._make_event_time(),
            market_date=date(2026, 5, 18),
            available_at=datetime(2026, 5, 18, 10, 30, tzinfo=CST),
            as_of_date=date(2026, 5, 17),
        )
        d = tc.to_dict()
        assert "available_at" in d
        assert "as_of_date" in d
