"""Tests for ActivityLog and ActivityType (ADR-010)."""

import json
import tempfile
import os
from pathlib import Path

import pytest

from synapse.core.activity import (
    ActivityLog,
    ActivityEntry,
    ActivityType,
    FORBIDDEN_TYPES,
)


class TestActivityType:
    """Tests for ActivityType enum values."""

    def test_thesis_created(self):
        assert ActivityType.THESIS_CREATED.value == "thesis.created"

    def test_thesis_revised(self):
        assert ActivityType.THESIS_REVISED.value == "thesis.revised"

    def test_decision_recorded(self):
        assert ActivityType.DECISION_RECORDED.value == "decision.recorded"

    def test_review_completed(self):
        assert ActivityType.REVIEW_COMPLETED.value == "review.completed"

    def test_watchlist_generated(self):
        assert ActivityType.WATCHLIST_GENERATED.value == "watchlist.generated"

    def test_position_opened(self):
        assert ActivityType.POSITION_OPENED.value == "position.opened"

    def test_position_closed(self):
        assert ActivityType.POSITION_CLOSED.value == "position.closed"

    def test_projection_rebuilt(self):
        assert ActivityType.PROJECTION_REBUILT.value == "projection.rebuilt"

    def test_workspace_indexed(self):
        assert ActivityType.WORKSPACE_INDEXED.value == "workspace.indexed"


class TestForbiddenTypes:
    """Tests for forbidden activity types."""

    def test_token_stream_forbidden(self):
        assert "token.stream" in FORBIDDEN_TYPES

    def test_llm_raw_reasoning_forbidden(self):
        assert "llm.raw.reasoning" in FORBIDDEN_TYPES

    def test_debug_spam_forbidden(self):
        assert "debug.spam" in FORBIDDEN_TYPES


class TestActivityEntry:
    """Tests for ActivityEntry serialization."""

    def test_to_jsonl(self):
        entry = ActivityEntry(
            ts="2026-05-18T10:00:00+08:00",
            type="thesis.created",
            obj_id="ths_7f8c91",
            actor="human",
            summary="创建消费恢复 thesis",
        )
        line = entry.to_jsonl()
        data = json.loads(line)
        assert data["ts"] == "2026-05-18T10:00:00+08:00"
        assert data["type"] == "thesis.created"
        assert data["obj_id"] == "ths_7f8c91"
        assert data["actor"] == "human"
        assert data["summary"] == "创建消费恢复 thesis"

    def test_from_dict(self):
        data = {
            "ts": "2026-05-18T10:00:00+08:00",
            "type": "thesis.created",
            "obj_id": "ths_7f8c91",
            "actor": "human",
            "summary": "创建消费恢复 thesis",
        }
        entry = ActivityEntry.from_dict(data)
        assert entry.ts == data["ts"]
        assert entry.type == data["type"]


class TestActivityLog:
    """Tests for ActivityLog append and read."""

    def test_append_and_read(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "activity.jsonl"
            log = ActivityLog(log_path)

            entry = log.append(
                activity_type="thesis.created",
                obj_id="ths_7f8c91",
                actor="human",
                summary="创建消费恢复 thesis",
                ts="2026-05-18T10:00:00+08:00",
            )
            assert entry.type == "thesis.created"
            assert entry.obj_id == "ths_7f8c91"

            entries = log.read_all()
            assert len(entries) == 1
            assert entries[0].type == "thesis.created"

    def test_append_multiple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "activity.jsonl"
            log = ActivityLog(log_path)

            log.append("thesis.created", "ths_1", "human", "创建 thesis 1")
            log.append("decision.recorded", "dec_1", "human", "记录决策 1")
            log.append("review.completed", "rev_1", "human", "完成回顾 1")

            entries = log.read_all()
            assert len(entries) == 3
            assert entries[0].type == "thesis.created"
            assert entries[1].type == "decision.recorded"
            assert entries[2].type == "review.completed"

    def test_forbidden_type_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "activity.jsonl"
            log = ActivityLog(log_path)

            with pytest.raises(ValueError, match="Forbidden activity type"):
                log.append("token.stream", "obj_1", "system", "test")

    def test_jsonl_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "activity.jsonl"
            log = ActivityLog(log_path)

            log.append(
                "thesis.created",
                "ths_7f8c91",
                "human",
                "创建消费恢复 thesis",
                ts="2026-05-18T10:00:00+08:00",
            )

            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["type"] == "thesis.created"

    def test_empty_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "activity.jsonl"
            log = ActivityLog(log_path)

            assert log.is_empty()
            assert log.count() == 0
            assert log.read_all() == []

    def test_read_nonexistent(self):
        log = ActivityLog("/nonexistent/activity.jsonl")
        assert log.read_all() == []
        assert log.is_empty()
