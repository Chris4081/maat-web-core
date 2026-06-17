from __future__ import annotations

import re
import time
from datetime import datetime
from hashlib import md5
from typing import Any

from .database import Database, now_iso
from .maat_memory_archive import archive_old_memories


def _settings(settings: Any) -> dict[str, Any]:
    if isinstance(settings, dict):
        return settings
    try:
        return vars(settings)
    except TypeError:
        return {}


def _compress(text: Any, limit: int = 320) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "…"


def _fingerprint(text: str) -> str:
    return md5(str(text or "").encode("utf-8", errors="ignore")).hexdigest()


def _split_tags(text: Any) -> list[str]:
    tags = []
    for item in re.split(r"[,;\s]+", str(text or "")):
        clean = item.strip().lower()
        if clean and clean not in tags:
            tags.append(clean)
    return tags


def _current_user(settings: Any) -> str:
    return str(_settings(settings).get("supermem_current_user") or "User").strip() or "User"


def _hours(settings: Any, hours: int | None) -> int:
    if hours is None:
        hours = _settings(settings).get("supermem_dream_hours", 24)
    try:
        return max(1, min(int(hours or 24), 168))
    except (TypeError, ValueError):
        return 24


def _dream_summary(category: str, memory_type: str, maat_field: str, author: str, rows: list[Any]) -> tuple[str, str]:
    ranked = sorted(
        rows,
        key=lambda row: (float(row["priority"] or 0), float(row["importance"] or 0), float(row["ts"] or 0)),
        reverse=True,
    )
    date = datetime.fromtimestamp(float(ranked[0]["ts"] or time.time())).strftime("%d.%m.%Y")
    header_parts = [f"[Maat-Dream:{category or 'allgemein'}]", f"{date}"]
    if author:
        header_parts.append(f"User={author}")
    if maat_field:
        header_parts.append(f"Feld={maat_field}")
    snippets = []
    tag_pool: list[str] = ["dream", "consolidated", category or "allgemein"]
    for row in ranked[:8]:
        content = row["content"] or row["compressed"] or ""
        if not content:
            continue
        snippets.append(_compress(content, 180))
        tag_pool.extend(_split_tags(row["tags"] or row["keywords"] or ""))
    if not snippets:
        snippets.append("keine verwertbaren Details")
    summary = "; ".join(snippets)
    content = " ".join(header_parts) + " " + summary
    tags = ",".join(dict.fromkeys(tag_pool[:18]))
    return content, tags


def run_memory_dreaming(database: Database, settings: Any, hours: int | None = None) -> dict[str, Any]:
    data = _settings(settings)
    if not data.get("supermem_dreaming_enabled", True):
        return {
            "ok": True,
            "hours": _hours(settings, hours),
            "source_rows": 0,
            "created": 0,
            "updated": 0,
            "dreams": [],
            "archive": {"ok": True, "archived": 0, "groups": 0, "skipped": "dreaming-disabled"},
            "skipped": "disabled",
        }
    span = _hours(settings, hours)
    cutoff = time.time() - span * 3600
    current_user = _current_user(settings)
    rows = database.connection.execute(
        """
        SELECT *
        FROM supermem_memories
        WHERE status='active'
          AND layer='episodic'
          AND ts >= ?
          AND content NOT LIKE '[Maat-Dream:%'
        ORDER BY ts DESC
        LIMIT 1000
        """,
        (cutoff,),
    ).fetchall()
    groups: dict[tuple[str, str, str, str], list[Any]] = {}
    for row in rows:
        author = str(row["author_user"] or "")
        if author and author != current_user:
            # Keep dreams autobiographically clean for the selected user.
            continue
        key = (
            str(row["category"] or "allgemein"),
            str(row["memory_type"] or "fact"),
            str(row["maat_field"] or ""),
            author,
        )
        groups.setdefault(key, []).append(row)

    now = now_iso()
    created = 0
    updated = 0
    dream_items: list[dict[str, Any]] = []
    for (category, memory_type, maat_field, author), group_rows in groups.items():
        if len(group_rows) < 3:
            continue
        content, tags = _dream_summary(category, memory_type, maat_field, author, group_rows)
        priority = max(float(row["priority"] or 0.5) for row in group_rows)
        importance = max(float(row["importance"] or 0.5) for row in group_rows)
        confidence = min(0.95, 0.58 + min(len(group_rows), 20) * 0.015)
        fp = _fingerprint(f"dream:{category}:{memory_type}:{maat_field}:{author}:{content}")
        existing = database.connection.execute("SELECT id FROM supermem_memories WHERE fp=?", (fp,)).fetchone()
        database.connection.execute(
            """
            INSERT INTO supermem_memories
              (layer, ts, role, author_user, content, compressed, keywords, category, memory_type,
               maat_field, tags, priority, importance, confidence, status, fp, hits, created_at, updated_at)
            VALUES ('semantic', ?, 'system', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, 1, ?, ?)
            ON CONFLICT(fp) DO UPDATE SET
              hits=hits+1,
              priority=MAX(priority, excluded.priority),
              importance=MAX(importance, excluded.importance),
              confidence=MAX(confidence, excluded.confidence),
              updated_at=excluded.updated_at
            """,
            (
                time.time(),
                author,
                content,
                _compress(content, 420),
                tags,
                category,
                memory_type,
                maat_field,
                tags,
                priority,
                importance,
                confidence,
                fp,
                now,
                now,
            ),
        )
        if existing:
            updated += 1
        else:
            created += 1
        dream_items.append(
            {
                "category": category,
                "memory_type": memory_type,
                "maat_field": maat_field,
                "author_user": author,
                "source_count": len(group_rows),
                "summary": _compress(content, 220),
            }
        )

    database.connection.commit()
    archive = archive_old_memories(database, settings)
    if data.get("supermem_debug", False):
        print(
            f"[MAAT Web Core][memory_dreaming] hours={span} rows={len(rows)} "
            f"created={created} updated={updated} archive={archive.get('archived', 0)}"
        )
    return {
        "ok": True,
        "hours": span,
        "source_rows": len(rows),
        "created": created,
        "updated": updated,
        "dreams": dream_items,
        "archive": archive,
    }
