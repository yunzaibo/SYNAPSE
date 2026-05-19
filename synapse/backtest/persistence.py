"""Parquet-based persistence for backtest results.

Provides save/load/query operations for BacktestRunResult using Parquet
format with schema versioning stored in file metadata. Supports lazy
upcast for backward compatibility when loading older schema versions.

Directory layout:
    results/{factor_id}/{run_id}.parquet           # Main result summary
    quintile_returns/{factor_id}/{run_id}.parquet   # Per-quintile returns
    ic_analysis/{factor_id}/{run_id}.parquet        # IC analysis results
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from synapse.backtest.result import (
    BacktestRunResult,
    ICAnalysisResult,
    PerformanceMetrics,
)

logger = logging.getLogger(__name__)

# Current schema version — bump when BacktestRunResult gains new fields
CURRENT_SCHEMA_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Path sanitisation — prevent path traversal
# ---------------------------------------------------------------------------

_DANGEROUS_CHARS = frozenset("/\\\x00")


def _sanitize_path_component(name: str) -> str:
    """Reject path traversal sequences in user-supplied directory names.

    Replaces ``/``, ``\\``, and null bytes with ``_`` and strips leading
    ``..`` segments.  Raises ``ValueError`` if the result is empty.
    """
    cleaned = name
    for ch in _DANGEROUS_CHARS:
        cleaned = cleaned.replace(ch, "_")
    # Strip leading dot-segments that could escape the base directory
    while cleaned.startswith(".."):
        cleaned = cleaned[2:].lstrip("_.")
    if not cleaned:
        raise ValueError(f"Path component cannot be empty after sanitisation: {name!r}")
    return cleaned


# ---------------------------------------------------------------------------
# Parquet I/O helpers
# ---------------------------------------------------------------------------


def _write_parquet_with_metadata(
    df: pd.DataFrame, path: Path, metadata: dict[str, str]
) -> None:
    """Write a DataFrame to Parquet with custom key-value metadata.

    Uses pyarrow directly because ``pd.DataFrame.to_parquet(metadata=...)``
    is not supported in pandas 2.1.x.
    """
    table = pa.Table.from_pandas(df, preserve_index=False)
    existing = table.schema.metadata or {}
    # Metadata values must be bytes
    encoded = {k.encode(): v.encode() for k, v in metadata.items()}
    new_meta = {**existing, **encoded}
    table = table.replace_schema_metadata(new_meta)
    pq.write_table(table, path, compression="snappy")


def _read_parquet_metadata(path: Path) -> dict[str, str]:
    """Read Parquet file metadata as a dict."""
    schema = pq.read_schema(path)
    raw = schema.metadata or {}
    return {k.decode(): v.decode() for k, v in raw.items()}


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


def save_result(result: BacktestRunResult, base_dir: str | Path) -> None:
    """Persist a BacktestRunResult to Parquet files.

    Creates three Parquet files under *base_dir*:

    - ``results/{factor_id}/{run_id}.parquet`` — scalar fields, performance
      metrics, long_short_returns, benchmark_returns, quintile_portfolios,
      attribution (JSON-encoded in columns).
    - ``quintile_returns/{factor_id}/{run_id}.parquet`` — per-quintile
      return rates as a tabular DataFrame.
    - ``ic_analysis/{factor_id}/{run_id}.parquet`` — IC time-series and
      summary statistics (only written when ``result.ic_analysis`` is set).

    Each file embeds ``schema_version`` in Parquet metadata.

    Args:
        result: The backtest result to persist.
        base_dir: Root directory for the results tree.
    """
    base = Path(base_dir)
    factor_id = _sanitize_path_component(result.factor_id or "default")
    run_id = _sanitize_path_component(result.id)
    schema_version = result.schema_version

    meta = {"schema_version": schema_version}

    # --- Main result summary ---
    summary_path = base / "results" / factor_id / f"{run_id}.parquet"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    summary_row = {
        "id": run_id,
        "schema_version": schema_version,
        "run_timestamp": result.run_timestamp,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "factor_id": factor_id,
        "status": result.status,
        "error": result.error or "",
        "config": json.dumps(result.config, ensure_ascii=False),
        "quintile_portfolios": json.dumps(
            [qp.to_dict() for qp in result.quintile_portfolios],
            ensure_ascii=False,
        ),
        "long_short_returns": json.dumps(result.long_short_returns),
        "benchmark_returns": json.dumps(result.benchmark_returns),
        "quintile_returns": json.dumps(result.quintile_returns),
    }
    # Flatten performance metrics
    perf = result.performance.to_dict()
    for k, v in perf.items():
        summary_row[f"perf_{k}"] = v
    # Flatten attribution if present
    if result.attribution:
        attr = result.attribution.to_dict()
        summary_row["attr_total_factor_return"] = attr["total_factor_return"]
        summary_row["attr_residual_return"] = attr["residual_return"]
        summary_row["attr_r_squared"] = attr["r_squared"]
        summary_row["attr_factor_returns"] = json.dumps(
            {str(k): v for k, v in attr["factor_returns"].items()}
        )
        summary_row["attr_residual_returns"] = json.dumps(attr["residual_returns"])
    else:
        summary_row["attr_total_factor_return"] = 0.0
        summary_row["attr_residual_return"] = 0.0
        summary_row["attr_r_squared"] = 0.0
        summary_row["attr_factor_returns"] = "{}"
        summary_row["attr_residual_returns"] = "[]"

    df_summary = pd.DataFrame([summary_row])
    _write_parquet_with_metadata(df_summary, summary_path, meta)
    logger.debug("Saved summary -> %s", summary_path)

    # --- Quintile returns ---
    qr_path = base / "quintile_returns" / factor_id / f"{run_id}.parquet"
    qr_path.parent.mkdir(parents=True, exist_ok=True)

    if result.quintile_returns:
        qr_rows = [
            {"quintile": q, "return": r}
            for q, r in sorted(result.quintile_returns.items())
        ]
    else:
        qr_rows = [{"quintile": 0, "return": 0.0}]

    df_qr = pd.DataFrame(qr_rows)
    _write_parquet_with_metadata(df_qr, qr_path, meta)
    logger.debug("Saved quintile returns -> %s", qr_path)

    # --- IC analysis ---
    if result.ic_analysis is not None:
        ic_path = base / "ic_analysis" / factor_id / f"{run_id}.parquet"
        ic_path.parent.mkdir(parents=True, exist_ok=True)

        ic = result.ic_analysis
        ic_row = {
            "factor_id": ic.factor_id,
            "ic_mean": ic.ic_mean,
            "ic_std": ic.ic_std,
            "icir": ic.icir,
            "rank_ic_mean": ic.rank_ic_mean,
            "rank_ic_std": ic.rank_ic_std,
            "rank_icir": ic.rank_icir,
            "ic_positive_ratio": ic.ic_positive_ratio,
            "ic_series": json.dumps(list(ic.ic_series)),
            "rank_ic_series": json.dumps(list(ic.rank_ic_series)),
            "rolling_ic": json.dumps(list(ic.rolling_ic)),
        }
        df_ic = pd.DataFrame([ic_row])
        _write_parquet_with_metadata(df_ic, ic_path, meta)
        logger.debug("Saved IC analysis -> %s", ic_path)


# ---------------------------------------------------------------------------
# Load helpers
# ---------------------------------------------------------------------------


def _lazy_upcast(row: dict, file_schema_version: str) -> dict:
    """Apply lazy upcast for older schema versions.

    Adds default values for fields introduced after *file_schema_version*.
    Currently schema 1.0 is the only version; this is a no-op placeholder
    for future schema evolution.
    """
    # Schema 1.0 -> 1.1 example (if we ever add a field):
    # if file_schema_version < "1.1":
    #     row.setdefault("new_field", "default_value")
    return row


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


def load_result(base_dir: str | Path, factor_id: str, run_id: str) -> BacktestRunResult:
    """Load a BacktestRunResult from Parquet files.

    Reads the summary, quintile returns, and (optionally) IC analysis
    files, applies lazy upcast based on stored schema_version, and
    reconstructs a BacktestRunResult.

    Args:
        base_dir: Root directory for the results tree.
        factor_id: Factor identifier sub-directory.
        run_id: Run identifier (filename stem).

    Returns:
        Reconstructed BacktestRunResult.

    Raises:
        FileNotFoundError: If the summary Parquet file does not exist.
    """
    base = Path(base_dir)
    factor_id = _sanitize_path_component(factor_id)
    run_id = _sanitize_path_component(run_id)
    summary_path = base / "results" / factor_id / f"{run_id}.parquet"

    if not summary_path.exists():
        raise FileNotFoundError(f"No backtest result found: {summary_path}")

    df_summary = pd.read_parquet(summary_path, engine="pyarrow")
    row = df_summary.iloc[0].to_dict()

    # Read schema_version from Parquet metadata (not the DataFrame column)
    file_meta = _read_parquet_metadata(summary_path)
    schema_version = file_meta.get("schema_version", CURRENT_SCHEMA_VERSION)

    # Lazy upcast
    row = _lazy_upcast(row, schema_version)

    # --- Parse JSON-encoded fields ---
    config = json.loads(row.get("config", "{}"))
    long_short_returns = tuple(json.loads(row.get("long_short_returns", "[]")))
    benchmark_returns = tuple(json.loads(row.get("benchmark_returns", "[]")))
    quintile_returns = {
        int(k): v for k, v in json.loads(row.get("quintile_returns", "{}")).items()
    }

    # Reconstruct quintile portfolios
    qp_raw = json.loads(row.get("quintile_portfolios", "[]"))
    quintile_portfolios = _reconstruct_quintile_portfolios(qp_raw)

    # Reconstruct performance metrics
    perf_dict = {}
    for k in PerformanceMetrics.__slots__:
        pk = f"perf_{k}"
        if pk in row:
            perf_dict[k] = row[pk]
    performance = PerformanceMetrics.from_dict(perf_dict) if perf_dict else PerformanceMetrics()

    # Reconstruct attribution
    attr = _reconstruct_attribution(row)

    # --- IC analysis ---
    ic_analysis = None
    ic_path = base / "ic_analysis" / factor_id / f"{run_id}.parquet"
    if ic_path.exists():
        df_ic = pd.read_parquet(ic_path, engine="pyarrow")
        ic_row = df_ic.iloc[0].to_dict()
        ic_analysis = ICAnalysisResult(
            factor_id=ic_row.get("factor_id", ""),
            ic_series=tuple(json.loads(ic_row.get("ic_series", "[]"))),
            rank_ic_series=tuple(json.loads(ic_row.get("rank_ic_series", "[]"))),
            ic_mean=ic_row.get("ic_mean", 0.0),
            ic_std=ic_row.get("ic_std", 0.0),
            icir=ic_row.get("icir", 0.0),
            rank_ic_mean=ic_row.get("rank_ic_mean", 0.0),
            rank_ic_std=ic_row.get("rank_ic_std", 0.0),
            rank_icir=ic_row.get("rank_icir", 0.0),
            rolling_ic=tuple(json.loads(ic_row.get("rolling_ic", "[]"))),
            ic_positive_ratio=ic_row.get("ic_positive_ratio", 0.0),
        )

    return BacktestRunResult(
        id=row["id"],
        schema_version=schema_version,
        config=config,
        run_timestamp=row.get("run_timestamp", ""),
        start_date=row.get("start_date", ""),
        end_date=row.get("end_date", ""),
        factor_id=row.get("factor_id", ""),
        quintile_portfolios=quintile_portfolios,
        quintile_returns=quintile_returns,
        long_short_returns=long_short_returns,
        benchmark_returns=benchmark_returns,
        performance=performance,
        ic_analysis=ic_analysis,
        attribution=attr,
        status=row.get("status", "pending"),
        error=row.get("error") or None,
    )


def _reconstruct_quintile_portfolios(qp_raw: list) -> tuple:
    """Reconstruct QuintilePortfolio objects from raw dicts."""
    from synapse.backtest.result import QuintilePortfolio
    from datetime import date as date_type

    portfolios = []
    for qp in qp_raw:
        quintiles = {int(k): tuple(v) for k, v in qp.get("quintiles", {}).items()}
        weights = {int(k): v for k, v in qp.get("weights", {}).items()}
        portfolios.append(
            QuintilePortfolio(
                date=date_type.fromisoformat(qp["date"]),
                quintiles=quintiles,
                weights=weights,
                factor_name=qp.get("factor_name", ""),
                universe_size=qp.get("universe_size", 0),
                valid_count=qp.get("valid_count", 0),
            )
        )
    return tuple(portfolios)


def _reconstruct_attribution(row: dict) -> Optional["AttributionResult"]:
    """Reconstruct AttributionResult from summary row."""
    from synapse.backtest.result import AttributionResult

    total_fr = row.get("attr_total_factor_return", 0.0)
    residual_r = row.get("attr_residual_return", 0.0)
    r_sq = row.get("attr_r_squared", 0.0)
    factor_returns_raw = row.get("attr_factor_returns", "{}")
    residual_returns_raw = row.get("attr_residual_returns", "[]")

    # If all defaults, no attribution was stored
    if total_fr == 0.0 and residual_r == 0.0 and r_sq == 0.0:
        factor_returns = json.loads(factor_returns_raw) if factor_returns_raw else {}
        if not factor_returns:
            return None

    factor_returns = {
        int(k): v for k, v in json.loads(factor_returns_raw).items()
    } if factor_returns_raw else {}
    residual_returns = tuple(json.loads(residual_returns_raw)) if residual_returns_raw else ()

    return AttributionResult(
        factor_returns=factor_returns,
        residual_returns=residual_returns,
        total_factor_return=total_fr,
        residual_return=residual_r,
        r_squared=r_sq,
    )


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


def query_results(
    base_dir: str | Path,
    start_date: str = "",
    end_date: str = "",
    factor_name: str | None = None,
) -> list[BacktestRunResult]:
    """Query persisted backtest results by date range and factor.

    Scans ``results/`` for Parquet files, reads metadata and key columns
    from each file, and returns matching BacktestRunResult objects.

    Args:
        base_dir: Root directory for the results tree.
        start_date: Inclusive start date filter (ISO format, e.g. "2024-01-01").
        end_date: Inclusive end date filter.
        factor_name: Optional factor_id filter.

    Returns:
        List of BacktestRunResult matching the query criteria.
    """
    base = Path(base_dir)
    results_dir = base / "results"

    if not results_dir.exists():
        return []

    matches: list[BacktestRunResult] = []

    # Glob all parquet files under results/
    factor_dirs = sorted(results_dir.iterdir()) if results_dir.is_dir() else []

    for factor_dir in factor_dirs:
        if not factor_dir.is_dir():
            continue

        fid = factor_dir.name

        # Apply factor_name filter early to skip unnecessary directories
        if factor_name and fid != factor_name:
            continue

        for pq_file in sorted(factor_dir.glob("*.parquet")):
            run_id = pq_file.stem

            # Quick date check from metadata/columns before full load
            try:
                df_meta = pd.read_parquet(pq_file, engine="pyarrow", columns=["start_date", "end_date"])
                file_start = df_meta.iloc[0].get("start_date", "")
                file_end = df_meta.iloc[0].get("end_date", "")
            except Exception:
                logger.warning("Skipping unreadable file: %s", pq_file)
                continue

            # Date range filter
            if start_date and file_end and file_end < start_date:
                continue
            if end_date and file_start and file_start > end_date:
                continue

            try:
                result = load_result(base, fid, run_id)
                matches.append(result)
            except Exception:
                logger.warning("Failed to load result: %s/%s", fid, run_id)

    return matches
