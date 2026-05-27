from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from app.core.logging import get_logger

logger = get_logger(__name__)

import os
_DB_PATH = Path(os.environ.get("STATS_DB_PATH", "/app/data/stats.db"))
_LOCK = threading.Lock()
_DB_CONN: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _DB_CONN
    if _DB_CONN is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _DB_CONN = sqlite3.connect(
            str(_DB_PATH),
            check_same_thread=False,
            isolation_level=None,  # autocommit — we manage transactions explicitly
        )
        _DB_CONN.row_factory = sqlite3.Row
        _DB_CONN.execute("PRAGMA journal_mode=WAL")   # concurrent reads while writing
        _DB_CONN.execute("PRAGMA synchronous=NORMAL")  # fsync on checkpoint, not every write
        _DB_CONN.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                intent       TEXT    NOT NULL,
                confidence   REAL    NOT NULL,
                processing_ms INTEGER NOT NULL,
                text_preview TEXT    NOT NULL,
                created_at   TEXT    NOT NULL
            )
        """)
        _DB_CONN.execute("CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at)")
        _DB_CONN.execute("CREATE INDEX IF NOT EXISTS idx_analyses_intent  ON analyses(intent)")
    return _DB_CONN


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    yield _get_conn()


class StatsService:

    def record(
        self,
        intent: str,
        confidence: float,
        processing_ms: int,
        text_preview: str,
    ) -> None:
        with _LOCK, _conn() as con:
            con.execute(
                "INSERT INTO analyses (intent, confidence, processing_ms, text_preview, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    intent,
                    confidence,
                    processing_ms,
                    text_preview[:120],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            con.commit()
        logger.debug("Stats recorded", intent=intent, ms=processing_ms)

    def get_kpis(self) -> dict:
        with _conn() as con:
            row = con.execute("""
                SELECT
                    COUNT(*)          AS total,
                    AVG(processing_ms) AS avg_ms,
                    AVG(confidence)    AS avg_confidence
                FROM analyses
            """).fetchone()

            total    = row["total"] or 0
            avg_ms   = int(row["avg_ms"] or 0)
            avg_conf = float(row["avg_confidence"] or 0.0)

            # Median: separate query to avoid COUNT(*) in OFFSET (unsupported in SQLite)
            if total > 0:
                half = total // 2
                median_row = con.execute(
                    "SELECT processing_ms FROM analyses ORDER BY processing_ms LIMIT 1 OFFSET ?",
                    (half,),
                ).fetchone()
                median_ms = int(median_row[0]) if median_row else avg_ms
            else:
                median_ms = 0

            # Resolution rate: % analyses with confidence >= 0.50
            if total > 0:
                high_conf = con.execute(
                    "SELECT COUNT(*) FROM analyses WHERE confidence >= 0.50"
                ).fetchone()[0]
                resolution_rate = round(high_conf / total * 100, 1)
            else:
                resolution_rate = 0.0

        return {
            "total_tickets": total,
            "resolution_rate": resolution_rate,
            "median_latency_ms": median_ms,
            "avg_latency_ms": avg_ms,
            "avg_confidence": round(avg_conf, 3),
        }

    def get_recent(self, limit: int = 10) -> list[dict]:
        with _conn() as con:
            rows = con.execute(
                """
                SELECT id, intent, confidence, processing_ms, text_preview, created_at
                FROM   analyses
                ORDER  BY created_at DESC
                LIMIT  ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_intent_distribution(self) -> list[dict]:
        with _conn() as con:
            total_row = con.execute("SELECT COUNT(*) FROM analyses").fetchone()
            total = total_row[0] or 1  # avoid div/0

            rows = con.execute(
                """
                SELECT intent, COUNT(*) AS count
                FROM   analyses
                GROUP  BY intent
                ORDER  BY count DESC
                """
            ).fetchall()

        return [
            {
                "intent": r["intent"],
                "count": r["count"],
                "pct": round(r["count"] / total * 100, 1),
            }
            for r in rows
        ]

    def get_drift_7days(self, top_intents: int = 3) -> list[dict]:
        with _conn() as con:
            # Determine top intents by volume
            top = [
                r["intent"]
                for r in con.execute(
                    "SELECT intent FROM analyses GROUP BY intent ORDER BY COUNT(*) DESC LIMIT ?",
                    (top_intents,),
                ).fetchall()
            ]
            if not top:
                return []

            # Daily totals per intent over last 7 days
            rows = con.execute(
                f"""
                SELECT
                    DATE(created_at) AS day,
                    intent,
                    COUNT(*)         AS cnt
                FROM analyses
                WHERE created_at >= DATE('now', '-7 days')
                  AND intent IN ({', '.join('?' * len(top))})
                GROUP BY day, intent
                ORDER BY day
                """,
                top,
            ).fetchall()

        # Pivot into [{date, intent1: pct, ...}]
        from collections import defaultdict
        daily: dict[str, dict[str, int]] = defaultdict(lambda: {i: 0 for i in top})
        daily_total: dict[str, int] = defaultdict(int)

        for r in rows:
            daily[r["day"]][r["intent"]] += r["cnt"]
            daily_total[r["day"]] += r["cnt"]

        result = []
        for day, counts in sorted(daily.items()):
            total = daily_total[day] or 1
            entry: dict = {"date": day}
            for intent in top:
                entry[intent] = round(counts.get(intent, 0) / total * 100, 1)
            result.append(entry)

        return result

    def get_alerts(self) -> list[dict]:
        dist = self.get_intent_distribution()
        if not dist:
            return []

        alerts = []
        for item in dist:
            if item["pct"] > 25:
                alerts.append({
                    "level": "warning",
                    "message": f"{item['intent']} représente {item['pct']}% des tickets — pic détecté",
                    "intent": item["intent"],
                })
            elif item["pct"] < 2 and item["count"] > 5:
                alerts.append({
                    "level": "info",
                    "message": f"{item['intent']} en baisse — {item['pct']}% seulement",
                    "intent": item["intent"],
                })

        if not alerts:
            alerts.append({
                "level": "ok",
                "message": "Distribution des intentions stable — aucune dérive détectée",
                "intent": None,
            })

        return alerts
