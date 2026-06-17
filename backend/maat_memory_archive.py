from __future__ import annotations

import re
import time
from datetime import datetime
from hashlib import md5
from typing import Any

from .database import Database, now_iso


def _settings(settings: Any) -> dict[str, Any]:
    if isinstance(settings, dict):
        return settings
    try:
        return vars(settings)
    except TypeError:
        return {}


def _compress(text: Any, limit: int = 280) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "…"


def _fingerprint(text: str) -> str:
    return md5(str(text or "").encode("utf-8", errors="ignore")).hexdigest()


def _month_bounds(ts: float) -> tuple[str, float, float]:
    dt = datetime.fromtimestamp(float(ts))
    start = datetime(dt.year, dt.month, 1)
    if dt.month == 12:
        end = datetime(dt.year + 1, 1, 1)
    else:
        end = datetime(dt.year, dt.month + 1, 1)
    return start.strftime("%Y-%m"), start.timestamp(), end.timestamp()


def initialize_memory_archive(database: Database) -> None:
    conn = database.connection
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS supermem_monthly_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT NOT NULL,
            period_start REAL NOT NULL,
            period_end REAL NOT NULL,
            author_user TEXT DEFAULT '',
            category TEXT DEFAULT 'allgemein',
            memory_type TEXT DEFAULT 'project',
            maat_field TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            summary TEXT NOT NULL,
            source_count INTEGER DEFAULT 0,
            priority REAL DEFAULT 0.50,
            importance REAL DEFAULT 0.50,
            status TEXT DEFAULT 'active',
            fp TEXT UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(period, author_user, category, memory_type, maat_field)
        )
        """
    )
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS sm_ar_period ON supermem_monthly_archive(period);
        CREATE INDEX IF NOT EXISTS sm_ar_window ON supermem_monthly_archive(period_start, period_end);
        CREATE INDEX IF NOT EXISTS sm_ar_author ON supermem_monthly_archive(author_user);
        CREATE INDEX IF NOT EXISTS sm_ar_status ON supermem_monthly_archive(status);
        """
    )
    conn.commit()


def _archive_summary(period: str, rows: list[Any]) -> str:
    ranked = sorted(
        rows,
        key=lambda row: (float(row["priority"] or 0), float(row["importance"] or 0), float(row["ts"] or 0)),
        reverse=True,
    )
    snippets = []
    for row in ranked[:10]:
        content = row["content"] or row["compressed"] or ""
        if not content:
            continue
        snippets.append(f"- {_compress(content, 180)}")
    if not snippets:
        snippets.append("- Keine verwertbaren Details.")
    return f"[MAAT-Archiv:{period}] Konsolidierte Erinnerungen:\n" + "\n".join(snippets)


def archive_old_memories(database: Database, settings: Any, after_days: int | None = None) -> dict[str, Any]:
    data = _settings(settings)
    if not data.get("supermem_archive_enabled", True):
        return {"ok": True, "archived": 0, "groups": 0, "skipped": "disabled"}

    days = after_days if after_days is not None else data.get("supermem_archive_after_days", 30)
    try:
        days = max(7, min(int(days or 30), 3650))
    except (TypeError, ValueError):
        days = 30
    cutoff = time.time() - days * 86400
    rows = database.connection.execute(
        """
        SELECT *
        FROM supermem_memories
        WHERE status='active' AND ts < ?
        ORDER BY ts ASC
        LIMIT 5000
        """,
        (cutoff,),
    ).fetchall()
    if not rows:
        return {"ok": True, "archived": 0, "groups": 0, "after_days": days}

    groups: dict[tuple[str, str, str, str, str], list[Any]] = {}
    for row in rows:
        period, start, end = _month_bounds(float(row["ts"]))
        key = (
            period,
            str(row["author_user"] or ""),
            str(row["category"] or "allgemein"),
            str(row["memory_type"] or "fact"),
            str(row["maat_field"] or ""),
        )
        groups.setdefault(key, []).append(row)

    now = now_iso()
    archived_ids: list[int] = []
    for (period, author, category, memory_type, maat_field), group_rows in groups.items():
        period, start, end = _month_bounds(float(group_rows[0]["ts"]))
        summary = _archive_summary(period, group_rows)
        tags = ",".join(
            sorted(
                {
                    tag.strip()
                    for row in group_rows
                    for tag in re.split(r"[,;\s]+", str(row["tags"] or row["keywords"] or ""))
                    if tag.strip()
                }
            )[:18]
        )
        priority = max(float(row["priority"] or 0.5) for row in group_rows)
        importance = max(float(row["importance"] or 0.5) for row in group_rows)
        fp = _fingerprint(f"{period}:{author}:{category}:{memory_type}:{maat_field}:{summary}")
        database.connection.execute(
            """
            INSERT INTO supermem_monthly_archive
              (period, period_start, period_end, author_user, category, memory_type, maat_field,
               tags, summary, source_count, priority, importance, status, fp, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
            ON CONFLICT(period, author_user, category, memory_type, maat_field) DO UPDATE SET
              tags=excluded.tags,
              summary=excluded.summary,
              source_count=excluded.source_count,
              priority=MAX(priority, excluded.priority),
              importance=MAX(importance, excluded.importance),
              status='active',
              updated_at=excluded.updated_at
            """,
            (
                period,
                start,
                end,
                author,
                category,
                memory_type,
                maat_field,
                tags,
                summary,
                len(group_rows),
                priority,
                importance,
                fp,
                now,
                now,
            ),
        )
        archived_ids.extend(int(row["id"]) for row in group_rows if row["id"] is not None)

    if archived_ids:
        placeholders = ",".join("?" for _ in archived_ids)
        database.connection.execute(
            f"UPDATE supermem_memories SET status='archived', updated_at=? WHERE id IN ({placeholders})",
            [now, *archived_ids],
        )
    database.connection.commit()
    if data.get("supermem_debug", False):
        print(f"[MAAT Web Core][memory_archive] archived={len(archived_ids)} groups={len(groups)} after_days={days}")
    return {"ok": True, "archived": len(archived_ids), "groups": len(groups), "after_days": days}


def recall_archive_for_window(database: Database, window: dict[str, Any], settings: Any, limit: int = 5) -> list[dict[str, Any]]:
    data = _settings(settings)
    if not data.get("supermem_archive_enabled", True):
        return []
    start = float(window.get("start") or 0)
    end = float(window.get("end") or 0)
    if start <= 0 or end <= 0:
        return []
    current_user = str(data.get("supermem_current_user") or "User")
    rows = database.connection.execute(
        """
        SELECT *
        FROM supermem_monthly_archive
        WHERE status='active'
          AND period_end > ?
          AND period_start < ?
          AND (author_user = ? OR author_user = '' OR author_user IS NULL)
        ORDER BY priority DESC, importance DESC, period_start DESC
        LIMIT ?
        """,
        (start, end, current_user, max(1, min(int(limit or 5), 20))),
    ).fetchall()
    out = []
    for row in rows:
        score = 0.78 + float(row["priority"] or 0.5) * 0.12 + float(row["importance"] or 0.5) * 0.08
        if row["author_user"] == current_user:
            score += float(data.get("supermem_user_memory_bonus", 0.12) or 0.12)
        out.append(
            {
                "id": row["id"],
                "source": "archive",
                "layer": "archive",
                "content": row["summary"] or "",
                "category": row["category"] or "allgemein",
                "memory_type": row["memory_type"] or "project",
                "maat_field": row["maat_field"] or "",
                "tags": row["tags"] or "",
                "author_user": row["author_user"] or "",
                "score": round(score, 3),
                "ts": (float(row["period_start"] or 0) + float(row["period_end"] or 0)) / 2.0,
                "time_window": row["period"] or window.get("label", ""),
                "source_count": int(row["source_count"] or 0),
            }
        )
    return out


def recall_archived_sources_for_window(database: Database, window: dict[str, Any], settings: Any, limit: int = 5) -> list[dict[str, Any]]:
    data = _settings(settings)
    if not data.get("supermem_archive_enabled", True):
        return []
    start = float(window.get("start") or 0)
    end = float(window.get("end") or 0)
    if start <= 0 or end <= 0:
        return []
    current_user = str(data.get("supermem_current_user") or "User")
    rows = database.connection.execute(
        """
        SELECT *
        FROM supermem_memories
        WHERE status='archived'
          AND ts >= ?
          AND ts < ?
          AND (author_user = ? OR author_user = '' OR author_user IS NULL)
        ORDER BY priority DESC, importance DESC, ts DESC
        LIMIT ?
        """,
        (start, end, current_user, max(1, min(int(limit or 5), 50))),
    ).fetchall()
    out = []
    for row in rows:
        content = row["content"] or row["compressed"] or ""
        score = 0.92 + float(row["priority"] or 0.5) * 0.16 + float(row["importance"] or 0.5) * 0.10
        if row["author_user"] == current_user:
            score += float(data.get("supermem_user_memory_bonus", 0.12) or 0.12)
        out.append(
            {
                "id": row["id"],
                "source": "archive_exact" if window.get("kind") == "day" else "archive_source",
                "layer": "archive_source",
                "content": content,
                "category": row["category"] or "allgemein",
                "memory_type": row["memory_type"] or "fact",
                "maat_field": row["maat_field"] or "",
                "tags": row["tags"] or "",
                "author_user": row["author_user"] or "",
                "score": round(score, 3),
                "ts": float(row["ts"] or 0),
                "time_window": window.get("label", ""),
            }
        )
    return out


def archive_stats(database: Database) -> dict[str, Any]:
    row = database.connection.execute(
        "SELECT COUNT(*) AS count, COALESCE(SUM(source_count), 0) AS sources FROM supermem_monthly_archive WHERE status='active'"
    ).fetchone()
    return {
        "monthly_archive": int(row["count"] or 0),
        "archived_sources": int(row["sources"] or 0),
    }
