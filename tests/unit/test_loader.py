"""Tests for Object Loader (TASK-003)."""

import tempfile
from pathlib import Path

import pytest

from synapse.core.loader import load_object, save_object, _detect_type, _OBJECT_TYPES
from synapse.core.schemas.base import BaseSchema
from synapse.core.schemas.thesis import Thesis, Confidence
from synapse.core.schemas.decision import Decision, DecisionType
from synapse.core.schemas.watchlist import WatchlistEntry
from synapse.core.schemas.signal import Signal
from synapse.core.schemas.risk import Risk
from synapse.core.schemas.event import Event
from synapse.core.schemas.topic import ResearchTopic
from synapse.core.schemas.position import Position
from synapse.core.schemas.review import Review


class TestDetectType:
    def test_detect_thesis(self):
        assert _detect_type({"id": "ths_7f8c91"}) is Thesis

    def test_detect_decision(self):
        assert _detect_type({"id": "dec_b4c5d6"}) is Decision

    def test_detect_watchlist(self):
        assert _detect_type({"id": "wl_a1b2c3"}) is WatchlistEntry

    def test_detect_signal(self):
        assert _detect_type({"id": "sig_a1b2c3"}) is Signal

    def test_detect_risk(self):
        assert _detect_type({"id": "rsk_d4e5f6"}) is Risk

    def test_detect_event(self):
        assert _detect_type({"id": "evt_k1l2m3"}) is Event

    def test_detect_topic(self):
        assert _detect_type({"id": "top_g7h8i9"}) is ResearchTopic

    def test_detect_position(self):
        assert _detect_type({"id": "pos_h1i2j3"}) is Position

    def test_detect_review(self):
        assert _detect_type({"id": "rev_e7f8g9"}) is Review

    def test_detect_unknown(self):
        assert _detect_type({"id": "xxx_123"}) is None

    def test_detect_no_id(self):
        assert _detect_type({}) is None


class TestSaveAndLoad:
    def test_save_and_load_thesis(self, tmp_path):
        th = Thesis(
            id="ths_test01",
            slug="test-thesis",
            title="测试 Thesis",
            thesis_statement="这是一个测试",
        )
        path = save_object(th, tmp_path / "ths_test01.yaml")
        assert path.exists()

        loaded = load_object(path)
        assert isinstance(loaded, Thesis)
        assert loaded.id == "ths_test01"
        assert loaded.title == "测试 Thesis"
        assert loaded.thesis_statement == "这是一个测试"

    def test_save_and_load_decision(self, tmp_path):
        dec = Decision(
            id="dec_test01",
            ticker="600519",
            decision_type=DecisionType.BUY,
            thesis="测试决策",
        )
        path = save_object(dec, tmp_path / "dec_test01.yaml")
        loaded = load_object(path)
        assert isinstance(loaded, Decision)
        assert loaded.decision_type == DecisionType.BUY

    def test_save_and_load_watchlist(self, tmp_path):
        wl = WatchlistEntry(id="wl_test01", ticker="600519", headline="测试关注")
        path = save_object(wl, tmp_path / "wl_test01.yaml")
        loaded = load_object(path)
        assert isinstance(loaded, WatchlistEntry)
        assert loaded.ticker == "600519"

    def test_save_and_load_signal(self, tmp_path):
        sig = Signal(id="sig_test01", description="测试信号")
        path = save_object(sig, tmp_path / "sig_test01.yaml")
        loaded = load_object(path)
        assert isinstance(loaded, Signal)

    def test_save_and_load_risk(self, tmp_path):
        rsk = Risk(id="rsk_test01", description="测试风险")
        path = save_object(rsk, tmp_path / "rsk_test01.yaml")
        loaded = load_object(path)
        assert isinstance(loaded, Risk)

    def test_save_and_load_event(self, tmp_path):
        evt = Event(id="evt_test01", title="测试事件")
        path = save_object(evt, tmp_path / "evt_test01.yaml")
        loaded = load_object(path)
        assert isinstance(loaded, Event)

    def test_save_and_load_topic(self, tmp_path):
        top = ResearchTopic(id="top_test01", name="测试主题")
        path = save_object(top, tmp_path / "top_test01.yaml")
        loaded = load_object(path)
        assert isinstance(loaded, ResearchTopic)

    def test_save_and_load_position(self, tmp_path):
        pos = Position(id="pos_test01", ticker="600519")
        path = save_object(pos, tmp_path / "pos_test01.yaml")
        loaded = load_object(path)
        assert isinstance(loaded, Position)

    def test_save_and_load_review(self, tmp_path):
        rev = Review(id="rev_test01", linked_decision_id="dec_test01")
        path = save_object(rev, tmp_path / "rev_test01.yaml")
        loaded = load_object(path)
        assert isinstance(loaded, Review)

    def test_save_creates_parent_dirs(self, tmp_path):
        th = Thesis(id="ths_test02", title="子目录测试")
        path = save_object(th, tmp_path / "sub" / "dir" / "ths_test02.yaml")
        assert path.exists()

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_object("nonexistent.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text("not a dict", encoding="utf-8")
        with pytest.raises(ValueError, match="Expected YAML dict"):
            load_object(path)

    def test_load_unknown_type(self, tmp_path):
        path = tmp_path / "unknown.yaml"
        path.write_text("id: xxx_123\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Cannot detect object type"):
            load_object(path)

    def test_round_trip_preserves_fields(self, tmp_path):
        """Full round-trip: create → save → load → compare."""
        th = Thesis(
            id="ths_rt01",
            slug="round-trip",
            title="往返测试",
            thesis_statement="测试字段保持",
            confidence=Confidence.HIGH,
            revision=3,
        )
        path = save_object(th, tmp_path / "ths_rt01.yaml")
        loaded = load_object(path)
        assert loaded.id == th.id
        assert loaded.slug == th.slug
        assert loaded.title == th.title
        assert loaded.thesis_statement == th.thesis_statement
        assert loaded.confidence.value == "high"
        assert loaded.revision == 3
