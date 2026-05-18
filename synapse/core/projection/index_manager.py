"""Index Manager — SQLite index for fast object queries.

ADR-009: FileWatcher + lazy rebuild.
- index_object() indexes a single research object
- query_objects() queries by type, status, ticker, date range
- Index is rebuildable from canonical artifacts (cache, not truth)
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from synapse.core.schemas.base import BaseSchema


# Default index path relative to workspace
DEFAULT_INDEX_DIR = ".index"
DEFAULT_DB_NAME = "workspace.db"

# Schema for the objects table
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS objects (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    ticker TEXT,
    symbol TEXT,
    market TEXT,
    status TEXT,
    created_at TEXT,
    updated_at TEXT,
    linked_thesis_id TEXT,
    data_json TEXT
);
"""

_CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_objects_type ON objects(type);",
    "CREATE INDEX IF NOT EXISTS idx_objects_ticker ON objects(ticker);",
    "CREATE INDEX IF NOT EXISTS idx_objects_status ON objects(status);",
    "CREATE INDEX IF NOT EXISTS idx_objects_created_at ON objects(created_at);",
]


def _detect_type(obj: BaseSchema) -> str:
    """Detect object type from class name."""
    class_name = type(obj).__name__
    type_map = {
        "Thesis": "thesis",
        "Decision": "decision",
        "Review": "review",
        "WatchlistEntry": "watchlist_entry",
        "Position": "position",
        "Signal": "signal",
        "Risk": "risk",
        "Event": "event",
        "ResearchTopic": "topic",
    }
    return type_map.get(class_name, "unknown")


class IndexManager:
    """SQLite index for fast research object queries.

    The index is rebuildable — it's a cache, not truth.
    Use index_object() to add/update, query_objects() to search.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        """Initialize the index manager.

        Args:
            db_path: Path to SQLite database file. If None, uses default.
        """
        if db_path is None:
            db_path = Path(DEFAULT_INDEX_DIR) / DEFAULT_DB_NAME

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy connection to SQLite database."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        self.conn.executescript(_CREATE_TABLE_SQL)
        for sql in _CREATE_INDEXES_SQL:
            self.conn.execute(sql)
        self.conn.commit()

    def index_object(self, obj: BaseSchema) -> None:
        """Index a single research object.

        Args:
            obj: Research object to index.
        """
        import json

        obj_type = _detect_type(obj)
        data = obj.to_dict()

        self.conn.execute(
            """
            INSERT OR REPLACE INTO objects
            (id, type, ticker, symbol, market, status, created_at, updated_at, linked_thesis_id, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obj.id,
                obj_type,
                data.get("ticker"),
                data.get("symbol"),
                data.get("market"),
                data.get("status"),
                data.get("created_at"),
                data.get("updated_at"),
                data.get("linked_thesis_id"),
                json.dumps(data, ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def index_objects(self, objects: list[BaseSchema]) -> int:
        """Index multiple research objects.

        Args:
            objects: List of research objects to index.

        Returns:
            Number of objects indexed.
        """
        import json

        rows = []
        for obj in objects:
            obj_type = _detect_type(obj)
            data = obj.to_dict()
            rows.append((
                obj.id,
                obj_type,
                data.get("ticker"),
                data.get("symbol"),
                data.get("market"),
                data.get("status"),
                data.get("created_at"),
                data.get("updated_at"),
                data.get("linked_thesis_id"),
                json.dumps(data, ensure_ascii=False),
            ))

        self.conn.executemany(
            """
            INSERT OR REPLACE INTO objects
            (id, type, ticker, symbol, market, status, created_at, updated_at, linked_thesis_id, data_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.conn.commit()
        return len(rows)

    def query_objects(
        self,
        obj_type: Optional[str] = None,
        ticker: Optional[str] = None,
        status: Optional[str] = None,
        linked_thesis_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query indexed objects with optional filters.

        Args:
            obj_type: Filter by object type (e.g. 'thesis', 'decision').
            ticker: Filter by ticker symbol.
            status: Filter by lifecycle status.
            linked_thesis_id: Filter by linked thesis ID.
            limit: Maximum number of results.

        Returns:
            List of dicts with object data.
        """
        conditions = []
        params = []

        if obj_type:
            conditions.append("type = ?")
            params.append(obj_type)
        if ticker:
            conditions.append("ticker = ?")
            params.append(ticker)
        if status:
            conditions.append("status = ?")
            params.append(status)
        if linked_thesis_id:
            conditions.append("linked_thesis_id = ?")
            params.append(linked_thesis_id)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM objects WHERE {where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def count_objects(self, obj_type: Optional[str] = None) -> int:
        """Count indexed objects.

        Args:
            obj_type: Optional type filter.

        Returns:
            Count of objects.
        """
        if obj_type:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM objects WHERE type = ?", (obj_type,)
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) FROM objects").fetchone()
        return row[0]

    def clear_index(self) -> None:
        """Clear all indexed data."""
        self.conn.execute("DELETE FROM objects")
        self.conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
