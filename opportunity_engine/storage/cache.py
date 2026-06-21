"""Caching and historical persistence.

A tiny TTL JSON file cache (used to avoid hammering rate-limited providers) plus
a SQLite writer that snapshots each scan's scores for the Phase-3 watchlist
performance / backtesting features. Both are best-effort and never raise into
the scan path.

Research only. Not financial advice.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


class Cache:
    """Filesystem JSON cache with per-entry TTL (seconds)."""

    def __init__(self, cache_dir: str = ".cache", ttl: int = 3600):
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl

    def _path(self, key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        return self.dir / f"{safe}.json"

    def get(self, key: str) -> Optional[Any]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
            if time.time() - payload.get("_ts", 0) > self.ttl:
                return None
            return payload.get("value")
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        try:
            self._path(key).write_text(json.dumps({"_ts": time.time(), "value": value}))
        except Exception:
            pass


def save_scan_history(result, db_path: str = "storage/sqlite/history.db") -> None:
    """Append the scan's ranked scores to a SQLite table for later analysis."""
    try:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.execute(
            """CREATE TABLE IF NOT EXISTS scan_history (
                as_of TEXT, ticker TEXT, rank INTEGER, final_score REAL,
                catalyst_score REAL, risk_level TEXT, current_price REAL,
                expected_upside_pct REAL,
                PRIMARY KEY (as_of, ticker)
            )"""
        )
        rows = [
            (
                result.as_of.isoformat(), o.ticker, o.rank, o.scores.final_score,
                o.scores.catalyst_score, o.risk.level.value, o.current_price,
                round(o.expected_upside_pct, 2),
            )
            for o in result.opportunities
        ]
        conn.executemany(
            "INSERT OR REPLACE INTO scan_history VALUES (?,?,?,?,?,?,?,?)", rows
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
