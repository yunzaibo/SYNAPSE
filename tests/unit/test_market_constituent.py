"""Tests for Index Constituent Module — synapse/core/market/constituent.py."""

from __future__ import annotations

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from synapse.core.market.constituent import (
    ConstituentChange,
    ConstituentSnapshot,
    IndexCode,
    constituent_tickers,
    is_member,
    load_constituent_changes,
    load_constituents,
)


# ---------------------------------------------------------------------------
# IndexCode enum
# ---------------------------------------------------------------------------


class TestIndexCode:
    """IndexCode enum values."""

    def test_csi300_value(self) -> None:
        assert IndexCode.CSI300.value == "000300.SH"

    def test_csi500_value(self) -> None:
        assert IndexCode.CSI500.value == "000905.SH"

    def test_csi1000_value(self) -> None:
        assert IndexCode.CSI1000.value == "000852.SH"

    def test_sse50_value(self) -> None:
        assert IndexCode.SSE50.value == "000016.SH"

    def test_custom_value(self) -> None:
        assert IndexCode.CUSTOM.value == "custom"

    def test_enum_member_count(self) -> None:
        assert len(IndexCode) == 5

    def test_str_enum(self) -> None:
        """IndexCode values are usable as plain strings."""
        code: str = IndexCode.CSI300
        assert code == "000300.SH"


# ---------------------------------------------------------------------------
# ConstituentSnapshot roundtrip
# ---------------------------------------------------------------------------


class TestConstituentSnapshot:
    """ConstituentSnapshot to_dict / from_dict roundtrip."""

    def test_roundtrip_with_weights(self) -> None:
        snap = ConstituentSnapshot(
            index_code="000300.SH",
            date=date(2025, 6, 30),
            members=frozenset(["600000.SH", "000001.SZ"]),
            weights={
                "600000.SH": Decimal("0.035"),
                "000001.SZ": Decimal("0.028"),
            },
        )
        d = snap.to_dict()
        restored = ConstituentSnapshot.from_dict(d)
        assert restored == snap
        assert restored.members == frozenset(["600000.SH", "000001.SZ"])
        assert restored.weights is not None
        assert restored.weights["600000.SH"] == Decimal("0.035")

    def test_roundtrip_no_weights(self) -> None:
        snap = ConstituentSnapshot(
            index_code="000905.SH",
            date=date(2025, 3, 15),
            members=frozenset(["300001.SZ"]),
            weights=None,
        )
        d = snap.to_dict()
        restored = ConstituentSnapshot.from_dict(d)
        assert restored == snap
        assert restored.weights is None

    def test_empty_members(self) -> None:
        snap = ConstituentSnapshot(
            index_code="000852.SH",
            date=date(2025, 1, 1),
            members=frozenset(),
            weights=None,
        )
        d = snap.to_dict()
        assert d["members"] == []
        restored = ConstituentSnapshot.from_dict(d)
        assert restored.members == frozenset()

    def test_to_dict_members_sorted(self) -> None:
        snap = ConstituentSnapshot(
            index_code="000300.SH",
            date=date(2025, 1, 1),
            members=frozenset(["B", "A", "C"]),
            weights=None,
        )
        d = snap.to_dict()
        assert d["members"] == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# ConstituentChange roundtrip
# ---------------------------------------------------------------------------


class TestConstituentChange:
    """ConstituentChange to_dict / from_dict roundtrip."""

    def test_roundtrip_add(self) -> None:
        change = ConstituentChange(
            date=date(2025, 6, 13),
            ticker="601318.SH",
            action="add",
            index_code="000300.SH",
            reason="rebalance",
        )
        d = change.to_dict()
        restored = ConstituentChange.from_dict(d)
        assert restored == change

    def test_roundtrip_remove(self) -> None:
        change = ConstituentChange(
            date=date(2025, 3, 21),
            ticker="000001.SZ",
            action="remove",
            index_code="000300.SH",
            reason="delist",
        )
        d = change.to_dict()
        restored = ConstituentChange.from_dict(d)
        assert restored == change

    def test_ipo_reason(self) -> None:
        change = ConstituentChange(
            date=date(2025, 9, 1),
            ticker="688001.SH",
            action="add",
            index_code="000905.SH",
            reason="ipo",
        )
        d = change.to_dict()
        assert d["reason"] == "ipo"
        restored = ConstituentChange.from_dict(d)
        assert restored.reason == "ipo"


# ---------------------------------------------------------------------------
# load_constituents — CSV I/O
# ---------------------------------------------------------------------------


class TestLoadConstituents:
    """load_constituents from CSV with date resolution."""

    def _write_members_csv(
        self, data_dir: Path, index_code: str, rows: list[dict]
    ) -> None:
        idx_dir = data_dir / "index" / index_code
        idx_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        df.to_csv(idx_dir / "members.csv", index=False)

    def test_exact_date_match(self, tmp_path: Path) -> None:
        self._write_members_csv(tmp_path, "000300.SH", [
            {"date": "2025-01-01", "ticker": "600000.SH"},
            {"date": "2025-01-01", "ticker": "000001.SZ"},
            {"date": "2025-06-30", "ticker": "600000.SH"},
            {"date": "2025-06-30", "ticker": "601318.SH"},
        ])
        snap = load_constituents("000300.SH", date(2025, 6, 30), data_dir=tmp_path)
        assert snap.members == frozenset(["600000.SH", "601318.SH"])
        assert snap.date == date(2025, 6, 30)

    def test_date_resolution_latest_before(self, tmp_path: Path) -> None:
        self._write_members_csv(tmp_path, "000300.SH", [
            {"date": "2025-01-01", "ticker": "A"},
            {"date": "2025-06-30", "ticker": "B"},
            {"date": "2025-12-31", "ticker": "C"},
        ])
        # Query July 15 → should resolve to June 30 snapshot
        snap = load_constituents("000300.SH", date(2025, 7, 15), data_dir=tmp_path)
        assert snap.members == frozenset(["B"])
        assert snap.date == date(2025, 6, 30)

    def test_future_date_uses_latest(self, tmp_path: Path) -> None:
        self._write_members_csv(tmp_path, "000300.SH", [
            {"date": "2025-01-01", "ticker": "X"},
        ])
        # Query far future → should use latest available
        snap = load_constituents("000300.SH", date(2099, 12, 31), data_dir=tmp_path)
        assert snap.members == frozenset(["X"])
        assert snap.date == date(2025, 1, 1)

    def test_date_before_all_snapshots(self, tmp_path: Path) -> None:
        self._write_members_csv(tmp_path, "000300.SH", [
            {"date": "2025-06-01", "ticker": "Y"},
        ])
        # Query date before any snapshot → uses earliest
        snap = load_constituents("000300.SH", date(2024, 1, 1), data_dir=tmp_path)
        assert snap.members == frozenset(["Y"])

    def test_with_weights(self, tmp_path: Path) -> None:
        self._write_members_csv(tmp_path, "000300.SH", [
            {"date": "2025-01-01", "ticker": "600000.SH", "weight": "0.035"},
            {"date": "2025-01-01", "ticker": "000001.SZ", "weight": "0.028"},
        ])
        snap = load_constituents("000300.SH", date(2025, 1, 1), data_dir=tmp_path)
        assert snap.weights is not None
        assert snap.weights["600000.SH"] == Decimal("0.035")
        assert snap.weights["000001.SZ"] == Decimal("0.028")

    def test_missing_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Index directory not found"):
            load_constituents("000300.SH", date(2025, 1, 1), data_dir=tmp_path)

    def test_empty_members(self, tmp_path: Path) -> None:
        """members.csv exists but is empty."""
        idx_dir = tmp_path / "index" / "000300.SH"
        idx_dir.mkdir(parents=True)
        (idx_dir / "members.csv").write_text("date,ticker\n")
        snap = load_constituents("000300.SH", date(2025, 1, 1), data_dir=tmp_path)
        assert snap.members == frozenset()

    def test_no_date_column(self, tmp_path: Path) -> None:
        """Single-snapshot file without date column."""
        idx_dir = tmp_path / "index" / "000300.SH"
        idx_dir.mkdir(parents=True)
        df = pd.DataFrame({"ticker": ["A", "B"]})
        df.to_csv(idx_dir / "members.csv", index=False)
        snap = load_constituents("000300.SH", date(2025, 1, 1), data_dir=tmp_path)
        assert snap.members == frozenset(["A", "B"])


# ---------------------------------------------------------------------------
# load_constituent_changes
# ---------------------------------------------------------------------------


class TestLoadConstituentChanges:
    """load_constituent_changes sorted by date."""

    def _write_changes_csv(
        self, data_dir: Path, index_code: str, rows: list[dict]
    ) -> None:
        idx_dir = data_dir / "index" / index_code
        idx_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        df.to_csv(idx_dir / "changes.csv", index=False)

    def test_sorted_by_date(self, tmp_path: Path) -> None:
        self._write_changes_csv(tmp_path, "000300.SH", [
            {"date": "2025-06-20", "ticker": "X", "action": "add", "reason": "rebalance"},
            {"date": "2025-03-15", "ticker": "Y", "action": "remove", "reason": "delist"},
            {"date": "2025-09-01", "ticker": "Z", "action": "add", "reason": "ipo"},
        ])
        changes = load_constituent_changes(
            "000300.SH", date(2025, 1, 1), date(2025, 12, 31), data_dir=tmp_path
        )
        assert len(changes) == 3
        dates = [c.date for c in changes]
        assert dates == sorted(dates)
        assert changes[0].ticker == "Y"
        assert changes[1].ticker == "X"
        assert changes[2].ticker == "Z"

    def test_date_range_filter(self, tmp_path: Path) -> None:
        self._write_changes_csv(tmp_path, "000300.SH", [
            {"date": "2025-01-01", "ticker": "A", "action": "add", "reason": "rebalance"},
            {"date": "2025-06-01", "ticker": "B", "action": "add", "reason": "rebalance"},
            {"date": "2025-12-01", "ticker": "C", "action": "add", "reason": "rebalance"},
        ])
        changes = load_constituent_changes(
            "000300.SH", date(2025, 3, 1), date(2025, 9, 30), data_dir=tmp_path
        )
        assert len(changes) == 1
        assert changes[0].ticker == "B"

    def test_no_changes_returns_empty(self, tmp_path: Path) -> None:
        changes = load_constituent_changes(
            "000300.SH", date(2025, 1, 1), date(2025, 12, 31), data_dir=tmp_path
        )
        assert changes == []

    def test_all_reasons(self, tmp_path: Path) -> None:
        reasons = ["rebalance", "ipo", "delist", "suspend"]
        rows = [
            {"date": f"2025-0{i+1}-01", "ticker": f"T{i}", "action": "add", "reason": r}
            for i, r in enumerate(reasons)
        ]
        self._write_changes_csv(tmp_path, "000300.SH", rows)
        changes = load_constituent_changes(
            "000300.SH", date(2025, 1, 1), date(2025, 12, 31), data_dir=tmp_path
        )
        assert len(changes) == 4
        assert {c.reason for c in changes} == set(reasons)


# ---------------------------------------------------------------------------
# is_member
# ---------------------------------------------------------------------------


class TestIsMember:
    """is_member true/false cases."""

    def _write_members_csv(
        self, data_dir: Path, index_code: str, rows: list[dict]
    ) -> None:
        idx_dir = data_dir / "index" / index_code
        idx_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        df.to_csv(idx_dir / "members.csv", index=False)

    def test_is_member_true(self, tmp_path: Path) -> None:
        self._write_members_csv(tmp_path, "000300.SH", [
            {"date": "2025-01-01", "ticker": "600000.SH"},
            {"date": "2025-01-01", "ticker": "000001.SZ"},
        ])
        assert is_member("000300.SH", "600000.SH", date(2025, 1, 1), data_dir=tmp_path) is True

    def test_is_member_false(self, tmp_path: Path) -> None:
        self._write_members_csv(tmp_path, "000300.SH", [
            {"date": "2025-01-01", "ticker": "600000.SH"},
        ])
        assert is_member("000300.SH", "999999.SH", date(2025, 1, 1), data_dir=tmp_path) is False

    def test_is_member_after_removal(self, tmp_path: Path) -> None:
        self._write_members_csv(tmp_path, "000300.SH", [
            {"date": "2025-01-01", "ticker": "600000.SH"},
            {"date": "2025-06-30", "ticker": "OTHER.SH"},
        ])
        # 600000.SH was present in Jan but not Jun
        assert is_member("000300.SH", "600000.SH", date(2025, 1, 1), data_dir=tmp_path) is True
        assert is_member("000300.SH", "600000.SH", date(2025, 6, 30), data_dir=tmp_path) is False


# ---------------------------------------------------------------------------
# constituent_tickers
# ---------------------------------------------------------------------------


class TestConstituentTickers:
    """constituent_tickers returns frozenset."""

    def _write_members_csv(
        self, data_dir: Path, index_code: str, rows: list[dict]
    ) -> None:
        idx_dir = data_dir / "index" / index_code
        idx_dir.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        df.to_csv(idx_dir / "members.csv", index=False)

    def test_returns_frozenset(self, tmp_path: Path) -> None:
        self._write_members_csv(tmp_path, "000300.SH", [
            {"date": "2025-01-01", "ticker": "A"},
            {"date": "2025-01-01", "ticker": "B"},
        ])
        result = constituent_tickers("000300.SH", date(2025, 1, 1), data_dir=tmp_path)
        assert isinstance(result, frozenset)
        assert result == frozenset({"A", "B"})

    def test_empty_index(self, tmp_path: Path) -> None:
        idx_dir = tmp_path / "index" / "000300.SH"
        idx_dir.mkdir(parents=True)
        (idx_dir / "members.csv").write_text("date,ticker\n")
        result = constituent_tickers("000300.SH", date(2025, 1, 1), data_dir=tmp_path)
        assert result == frozenset()
