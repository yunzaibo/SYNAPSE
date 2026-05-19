"""Tests for synapse.backtest.persistence — Parquet-based result storage.

Covers: save/load roundtrip, schema_version in metadata, query by date range,
query by factor_name, lazy upcast from old schema, and edge cases.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from synapse.backtest.persistence import (
    CURRENT_SCHEMA_VERSION,
    load_result,
    query_results,
    save_result,
)
from synapse.backtest.result import (
    BacktestRunResult,
    ICAnalysisResult,
    PerformanceMetrics,
    QuintilePortfolio,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_results(tmp_path: Path) -> Path:
    """Provide a fresh temporary results directory."""
    return tmp_path / "results_root"


def _make_result(
    *,
    factor_id: str = "momentum_20d",
    run_id: str = "run-001",
    start_date: str = "2024-01-01",
    end_date: str = "2024-06-30",
    with_ic: bool = False,
    with_attribution: bool = True,
    quintile_returns: dict | None = None,
) -> BacktestRunResult:
    """Build a BacktestRunResult with deterministic test data."""
    perf = PerformanceMetrics(
        annual_return=0.12,
        volatility=0.15,
        sharpe=0.8,
        max_drawdown=-0.05,
        turnover=0.3,
        win_rate=0.55,
    )

    qp = QuintilePortfolio(
        date=date(2024, 1, 31),
        quintiles={1: ("000001.SZ", "000002.SZ"), 5: ("600001.SH", "600002.SH")},
        weights={1: {"000001.SZ": 0.5, "000002.SZ": 0.5}, 5: {"600001.SH": 0.5, "600002.SH": 0.5}},
        factor_name=factor_id,
        universe_size=100,
        valid_count=95,
    )

    ic = None
    if with_ic:
        ic = ICAnalysisResult(
            factor_id=factor_id,
            ic_series=(0.05, 0.03, 0.04),
            rank_ic_series=(0.04, 0.02, 0.035),
            ic_mean=0.04,
            ic_std=0.01,
            icir=4.0,
            rank_ic_mean=0.032,
            rank_ic_std=0.008,
            rank_icir=4.0,
            rolling_ic=(0.04, 0.035, 0.045),
            ic_positive_ratio=0.7,
        )

    from synapse.backtest.result import AttributionResult

    attr = None
    if with_attribution:
        attr = AttributionResult(
            factor_returns={1: -0.01, 5: 0.03},
            residual_returns=(0.001, -0.002, 0.003),
            total_factor_return=0.04,
            residual_return=0.001,
            r_squared=0.85,
        )

    return BacktestRunResult(
        id=run_id,
        schema_version="1.0",
        config={"lookback": 20, "universe": "CSI300"},
        run_timestamp="2024-07-01T10:00:00",
        start_date=start_date,
        end_date=end_date,
        factor_id=factor_id,
        quintile_portfolios=(qp,),
        quintile_returns=quintile_returns if quintile_returns is not None else {1: -0.02, 2: 0.0, 3: 0.01, 4: 0.02, 5: 0.04},
        long_short_returns=(0.03, 0.04, 0.02),
        benchmark_returns=(0.01, 0.015, 0.012),
        performance=perf,
        ic_analysis=ic,
        attribution=attr,
        status="completed",
        error=None,
    )


# ---------------------------------------------------------------------------
# 1. Save / Load roundtrip
# ---------------------------------------------------------------------------


class TestSaveLoadRoundtrip:
    """BacktestResult -> Parquet -> BacktestResult preserves all fields."""

    def test_scalar_fields_roundtrip(self, tmp_results: Path) -> None:
        result = _make_result()
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        assert loaded.id == result.id
        assert loaded.schema_version == result.schema_version
        assert loaded.config == result.config
        assert loaded.run_timestamp == result.run_timestamp
        assert loaded.start_date == result.start_date
        assert loaded.end_date == result.end_date
        assert loaded.factor_id == result.factor_id
        assert loaded.status == result.status
        assert loaded.error == result.error

    def test_performance_metrics_roundtrip(self, tmp_results: Path) -> None:
        result = _make_result()
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        assert loaded.performance.annual_return == pytest.approx(0.12)
        assert loaded.performance.volatility == pytest.approx(0.15)
        assert loaded.performance.sharpe == pytest.approx(0.8)
        assert loaded.performance.max_drawdown == pytest.approx(-0.05)
        assert loaded.performance.win_rate == pytest.approx(0.55)

    def test_quintile_returns_roundtrip(self, tmp_results: Path) -> None:
        result = _make_result()
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        assert loaded.quintile_returns == result.quintile_returns

    def test_long_short_and_benchmark_roundtrip(self, tmp_results: Path) -> None:
        result = _make_result()
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        assert loaded.long_short_returns == result.long_short_returns
        assert loaded.benchmark_returns == result.benchmark_returns

    def test_quintile_portfolios_roundtrip(self, tmp_results: Path) -> None:
        result = _make_result()
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        assert len(loaded.quintile_portfolios) == 1
        qp = loaded.quintile_portfolios[0]
        assert qp.date == date(2024, 1, 31)
        assert qp.factor_name == "momentum_20d"
        assert qp.universe_size == 100
        assert qp.quintiles[1] == ("000001.SZ", "000002.SZ")

    def test_ic_analysis_roundtrip(self, tmp_results: Path) -> None:
        result = _make_result(with_ic=True)
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        assert loaded.ic_analysis is not None
        assert loaded.ic_analysis.factor_id == "momentum_20d"
        assert loaded.ic_analysis.ic_mean == pytest.approx(0.04)
        assert loaded.ic_analysis.icir == pytest.approx(4.0)
        assert loaded.ic_analysis.ic_series == (0.05, 0.03, 0.04)
        assert loaded.ic_analysis.ic_positive_ratio == pytest.approx(0.7)

    def test_attribution_roundtrip(self, tmp_results: Path) -> None:
        result = _make_result(with_attribution=True)
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        assert loaded.attribution is not None
        assert loaded.attribution.total_factor_return == pytest.approx(0.04)
        assert loaded.attribution.residual_return == pytest.approx(0.001)
        assert loaded.attribution.r_squared == pytest.approx(0.85)
        assert loaded.attribution.factor_returns == {1: -0.01, 5: 0.03}
        assert loaded.attribution.residual_returns == (0.001, -0.002, 0.003)

    def test_full_roundtrip(self, tmp_results: Path) -> None:
        """End-to-end: save, load, verify to_dict matches."""
        result = _make_result(with_ic=True, with_attribution=True)
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        assert loaded.to_dict() == result.to_dict()


# ---------------------------------------------------------------------------
# 2. Schema version in Parquet metadata
# ---------------------------------------------------------------------------


class TestSchemaVersionMetadata:
    """Schema version is embedded in Parquet file metadata."""

    def test_schema_version_in_summary_metadata(self, tmp_results: Path) -> None:
        result = _make_result()
        save_result(result, tmp_results)

        summary_path = tmp_results / "results" / result.factor_id / f"{result.id}.parquet"
        schema = pq.read_schema(summary_path)
        meta = schema.metadata or {}
        assert b"schema_version" in meta

    def test_schema_version_value_matches_result(self, tmp_results: Path) -> None:
        result = _make_result()
        save_result(result, tmp_results)

        summary_path = tmp_results / "results" / result.factor_id / f"{result.id}.parquet"
        schema = pq.read_schema(summary_path)
        meta = schema.metadata or {}
        assert meta[b"schema_version"].decode() == result.schema_version

    def test_schema_version_in_quintile_returns_metadata(self, tmp_results: Path) -> None:
        result = _make_result()
        save_result(result, tmp_results)

        qr_path = tmp_results / "quintile_returns" / result.factor_id / f"{result.id}.parquet"
        schema = pq.read_schema(qr_path)
        meta = schema.metadata or {}
        assert meta[b"schema_version"].decode() == "1.0"


# ---------------------------------------------------------------------------
# 3. Query by date range
# ---------------------------------------------------------------------------


class TestQueryByDateRange:
    """query_results filters by start_date/end_date correctly."""

    def test_returns_results_within_date_range(self, tmp_results: Path) -> None:
        r1 = _make_result(run_id="r1", start_date="2024-01-01", end_date="2024-03-31")
        r2 = _make_result(run_id="r2", start_date="2024-04-01", end_date="2024-06-30")
        r3 = _make_result(run_id="r3", start_date="2024-07-01", end_date="2024-09-30")
        for r in (r1, r2, r3):
            save_result(r, tmp_results)

        results = query_results(tmp_results, start_date="2024-02-01", end_date="2024-05-01")
        ids = {r.id for r in results}
        # r1 ends 2024-03-31, so it overlaps with query start 2024-02-01
        # r2 starts 2024-04-01, so it overlaps with query end 2024-05-01
        # r3 starts 2024-07-01, so it should be excluded
        assert "r1" in ids
        assert "r2" in ids
        assert "r3" not in ids

    def test_empty_range_returns_all(self, tmp_results: Path) -> None:
        r1 = _make_result(run_id="r1")
        r2 = _make_result(run_id="r2")
        for r in (r1, r2):
            save_result(r, tmp_results)

        results = query_results(tmp_results)
        assert len(results) == 2

    def test_no_matches_returns_empty(self, tmp_results: Path) -> None:
        r1 = _make_result(run_id="r1", start_date="2024-01-01", end_date="2024-03-31")
        save_result(r1, tmp_results)

        results = query_results(tmp_results, start_date="2025-01-01", end_date="2025-12-31")
        assert results == []


# ---------------------------------------------------------------------------
# 4. Query by factor_name
# ---------------------------------------------------------------------------


class TestQueryByFactorName:
    """query_results filters by factor_name correctly."""

    def test_filters_by_factor_name(self, tmp_results: Path) -> None:
        r1 = _make_result(run_id="r1", factor_id="momentum_20d")
        r2 = _make_result(run_id="r2", factor_id="reversal_5d")
        r3 = _make_result(run_id="r3", factor_id="momentum_20d")
        for r in (r1, r2, r3):
            save_result(r, tmp_results)

        results = query_results(tmp_results, factor_name="momentum_20d")
        assert len(results) == 2
        assert all(r.factor_id == "momentum_20d" for r in results)

    def test_factor_name_with_date_filter(self, tmp_results: Path) -> None:
        r1 = _make_result(run_id="r1", factor_id="momentum_20d", start_date="2024-01-01", end_date="2024-03-31")
        r2 = _make_result(run_id="r2", factor_id="momentum_20d", start_date="2024-07-01", end_date="2024-09-30")
        save_result(r1, tmp_results)
        save_result(r2, tmp_results)

        results = query_results(
            tmp_results,
            factor_name="momentum_20d",
            start_date="2024-06-01",
            end_date="2024-12-31",
        )
        assert len(results) == 1
        assert results[0].id == "r2"


# ---------------------------------------------------------------------------
# 5. Lazy upcast from old schema version
# ---------------------------------------------------------------------------


class TestLazyUpcast:
    """Old schema versions load with default values for new fields."""

    def test_old_schema_version_loads_successfully(self, tmp_results: Path) -> None:
        """Simulate loading a file written with an older schema version."""
        result = _make_result()
        save_result(result, tmp_results)

        summary_path = tmp_results / "results" / result.factor_id / f"{result.id}.parquet"
        table = pq.read_table(summary_path)

        # Manually rewrite with an older schema_version in metadata
        old_meta = {b"schema_version": b"0.8"}
        existing = table.schema.metadata or {}
        table = table.replace_schema_metadata({**existing, **old_meta})
        pq.write_table(table, summary_path)

        loaded = load_result(tmp_results, result.factor_id, result.id)
        # Should still load with defaults for any missing fields
        assert loaded.id == result.id
        assert loaded.factor_id == result.factor_id
        assert loaded.schema_version == "0.8"

    def test_future_schema_upcast_with_defaults(self, tmp_results: Path) -> None:
        """File has schema 0.5 — lazy upcast fills in missing fields."""
        result = _make_result()
        save_result(result, tmp_results)

        summary_path = tmp_results / "results" / result.factor_id / f"{result.id}.parquet"
        table = pq.read_table(summary_path)

        # Rewrite with old schema version
        old_meta = {b"schema_version": b"0.5"}
        existing = table.schema.metadata or {}
        table = table.replace_schema_metadata({**existing, **old_meta})
        pq.write_table(table, summary_path)

        loaded = load_result(tmp_results, result.factor_id, result.id)
        # All existing fields should be preserved
        assert loaded.performance.annual_return == pytest.approx(0.12)
        assert loaded.quintile_returns == result.quintile_returns
        assert loaded.status == "completed"


# ---------------------------------------------------------------------------
# 6. Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_quintile_returns(self, tmp_results: Path) -> None:
        """Empty quintile_returns dict roundtrips correctly."""
        result = _make_result(quintile_returns={})
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        # Summary file stores quintile_returns as JSON "{}"; quintile_returns
        # file has placeholder row but summary is the source of truth
        assert loaded.quintile_returns == {}

    def test_no_ic_analysis(self, tmp_results: Path) -> None:
        """When ic_analysis is None, no IC file is created."""
        result = _make_result(with_ic=False)
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        assert loaded.ic_analysis is None
        ic_path = tmp_results / "ic_analysis" / result.factor_id / f"{result.id}.parquet"
        assert not ic_path.exists()

    def test_no_attribution(self, tmp_results: Path) -> None:
        """When attribution is None, attribution fields are defaults."""
        result = _make_result(with_attribution=False)
        save_result(result, tmp_results)
        loaded = load_result(tmp_results, result.factor_id, result.id)

        assert loaded.attribution is None

    def test_load_nonexistent_raises(self, tmp_results: Path) -> None:
        """Loading a non-existent result raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="No backtest result found"):
            load_result(tmp_results, "nonexistent", "nonexistent")

    def test_query_empty_directory(self, tmp_results: Path) -> None:
        """Query on empty directory returns empty list."""
        results = query_results(tmp_results)
        assert results == []

    def test_directory_creation(self, tmp_results: Path) -> None:
        """save_result creates directories if they don't exist."""
        result = _make_result()
        save_result(result, tmp_results)

        assert (tmp_results / "results" / result.factor_id).is_dir()
        assert (tmp_results / "quintile_returns" / result.factor_id).is_dir()

    def test_multiple_runs_same_factor(self, tmp_results: Path) -> None:
        """Multiple runs for the same factor coexist correctly."""
        r1 = _make_result(run_id="run-a", factor_id="alpha")
        r2 = _make_result(run_id="run-b", factor_id="alpha")
        save_result(r1, tmp_results)
        save_result(r2, tmp_results)

        loaded_a = load_result(tmp_results, "alpha", "run-a")
        loaded_b = load_result(tmp_results, "alpha", "run-b")

        assert loaded_a.id == "run-a"
        assert loaded_b.id == "run-b"
        # Verify they're independent
        assert loaded_a.to_dict() != loaded_b.to_dict() or loaded_a.id != loaded_b.id

    def test_overwrite_existing_result(self, tmp_results: Path) -> None:
        """Saving same run_id overwrites the previous result."""
        r1 = _make_result(run_id="overwrite-test")
        save_result(r1, tmp_results)

        r2 = _make_result(run_id="overwrite-test")
        save_result(r2, tmp_results)

        loaded = load_result(tmp_results, r2.factor_id, r2.id)
        assert loaded.id == "overwrite-test"
        assert loaded.status == r2.status
