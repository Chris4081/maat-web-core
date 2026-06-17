from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from .config import DATA_DIR, RuntimeSettings
from .database import Database, visible_message_text


DB_PATH = DATA_DIR / "chat_search.sqlite"
SESSION: dict[str, Any] = {"last_scan": 0.0, "last_status": {}}

DETAILS_RE = re.compile(r"(?is)<details\b.*?</details>")
INTERNAL_RE = re.compile(r"(?is)\[(?:MAAT_INTERNAL|MAAT_CHAT_SUMMARY|MAAT_CHAT_MEMORY)[^\]]*\].*?\[/[A-Z_]+\]")
THINK_RE = re.compile(r"(?is)<(?:think|thinking|reasoning)\b.*?</(?:think|thinking|reasoning)>")
PROGRESS_RE = re.compile(r"(?is)<div\b[^>]*class=['\"][^'\"]*maat-progress-card[^'\"]*['\"][^>]*>.*?(?:</div>\s*){1,8}")
HTML_RE = re.compile(r"(?is)<[^>]+>")


def initialize_chat_search(database: Database | None = None, settings: RuntimeSettings | None = None) -> None:
    _ensure_schema()
    if settings and getattr(settings, "chat_search_debug", False):
        print(f"[MAAT Web Core][chat_search] DB={DB_PATH}", flush=True)


def _debug(settings: RuntimeSettings, *parts: Any) -> None:
    if getattr(settings, "chat_search_debug", False):
        print("[MAAT Web Core][chat_search]", *parts, flush=True)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS indexed_files (
                path TEXT PRIMARY KEY,
                source TEXT NOT NULL DEFAULT 'external',
                mtime REAL NOT NULL,
                size INTEGER NOT NULL,
                indexed_at REAL NOT NULL,
                docs INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        _ensure_column(conn, "indexed_files", "source", "TEXT NOT NULL DEFAULT 'external'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_docs (
                id INTEGER PRIMARY KEY,
                source TEXT NOT NULL DEFAULT 'external',
                path TEXT NOT NULL,
                chat_id INTEGER,
                chat_name TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                timestamp TEXT DEFAULT '',
                user_text TEXT DEFAULT '',
                assistant_text TEXT DEFAULT '',
                text TEXT NOT NULL,
                file_mtime REAL NOT NULL
            )
            """
        )
        _ensure_column(conn, "chat_docs", "source", "TEXT NOT NULL DEFAULT 'external'")
        _ensure_column(conn, "chat_docs", "chat_id", "INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS chat_docs_path_idx ON chat_docs(path)")
        conn.execute("CREATE INDEX IF NOT EXISTS chat_docs_chat_idx ON chat_docs(chat_name)")
        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS chat_docs_fts USING fts5(
                    text,
                    user_text,
                    assistant_text,
                    chat_name,
                    content='chat_docs',
                    content_rowid='id',
                    tokenize='unicode61 remove_diacritics 2'
                )
                """
            )
        except sqlite3.OperationalError:
            pass


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _external_roots(settings: RuntimeSettings) -> list[Path]:
    raw = str(getattr(settings, "chat_search_external_roots", "") or "")
    pieces = re.split(r"[\n,]+", raw)
    roots: list[Path] = []
    seen: set[str] = set()
    for piece in pieces:
        value = piece.strip()
        if not value:
            continue
        path = Path(value).expanduser()
        if not path.exists() or not path.is_dir():
            continue
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        roots.append(path.resolve())
    return roots


def _iter_external_chat_files(settings: RuntimeSettings) -> list[Path]:
    seen: set[str] = set()
    files: list[Path] = []
    for root in _external_roots(settings):
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
                continue
            sp = str(path)
            if sp in seen:
                continue
            seen.add(sp)
            files.append(path)
    return files


def _is_progress_artifact(value: Any) -> bool:
    raw = html.unescape(str(value or ""))
    return bool(
        "maat-progress-card" in raw
        or "MAAT verarbeitet den Kontext" in raw
        or "Prompt wird vorbereitet" in raw
        or "Die Antwort startet gleich" in raw
    )


def is_chat_search_turn(text: str) -> bool:
    raw = (text or "").strip().lower()
    if not raw:
        return False
    return bool(
        re.match(r"^/maat\s+(?:chat\s+)?search\b", raw)
        or re.match(r"^/maat\s+(?:archive|archiv)\s+search\b", raw)
        or re.match(r"^/chat\s+search\b", raw)
        or re.match(r"^(?:finde|such(?:e)?|durchsuche)\s+(?:den\s+)?chats?\s+(?:über|ueber|zu|nach)\s+", raw)
        or re.match(r"^(?:such(?:e)?|durchsuche)\s+im\s+(?:archiv|chat|chatverlauf|chat-archiv)\s+", raw)
        or re.match(r"^(?:wann|wo)\s+haben\s+wir\s+(?:über|ueber)\s+.+?\s+gesprochen\??$", raw)
    )


def clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = PROGRESS_RE.sub(" ", text)
    text = DETAILS_RE.sub(" ", text)
    text = INTERNAL_RE.sub(" ", text)
    text = THINK_RE.sub(" ", text)
    text = HTML_RE.sub(" ", text)
    text = re.sub(r"(?is)\bsave\s*:\s*[\(\{].*?$", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _shorten(text: str, limit: int = 260) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _file_timestamp(path: Path) -> str:
    match = re.search(r"(20\d{2})(\d{2})(\d{2})[-_](\d{2})[-_](\d{2})[-_](\d{2})", path.stem)
    if match:
        y, mo, d, h, mi, _s = match.groups()
        return f"{y}-{mo}-{d} {h}:{mi}"
    try:
        return dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def _read_json(path: Path) -> Any:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".jsonl":
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        return rows
    return json.loads(text)


def _chat_name(path: Path, data: Any) -> str:
    title = ""
    if isinstance(data, dict):
        meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        title = str(meta.get("chat_title") or meta.get("title") or meta.get("name") or "").strip()
    if not title:
        title = path.stem
    parent = path.parent.name
    if parent and parent not in {"logs", "chat", "instruct", "user_data"}:
        return f"{parent} / {title}"
    return title


def _metadata_ts(meta: dict[str, Any], role: str, idx: int, fallback: str) -> str:
    value = meta.get(f"{role}_{idx}") if isinstance(meta, dict) else None
    if isinstance(value, dict):
        return str(value.get("timestamp") or fallback)
    return fallback


def _pairs_from_pair_list(pairs: Any, metadata: dict[str, Any], fallback_ts: str):
    if not isinstance(pairs, list):
        return
    for i, pair in enumerate(pairs):
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        if _is_progress_artifact(pair[1]):
            continue
        user_text = clean_text(pair[0])
        assistant_text = clean_text(pair[1])
        if is_chat_search_turn(user_text):
            continue
        if not user_text and not assistant_text:
            continue
        yield i, _metadata_ts(metadata, "user", i, fallback_ts), user_text, assistant_text


def _pairs_from_messages(messages: Any, fallback_ts: str):
    if not isinstance(messages, list):
        return
    turn = 0
    pending_user = ""
    pending_ts = fallback_ts
    skip_next_assistant = False
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or item.get("from") or item.get("speaker") or "").lower()
        raw_content = item.get("content") or item.get("text") or item.get("message") or ""
        if _is_progress_artifact(raw_content):
            continue
        content = clean_text(raw_content)
        ts = str(item.get("timestamp") or item.get("time") or fallback_ts)
        if not content:
            continue
        if role in {"user", "human", "you"}:
            if is_chat_search_turn(content):
                pending_user = ""
                skip_next_assistant = True
                continue
            if pending_user:
                yield turn, pending_ts, pending_user, ""
                turn += 1
            pending_user = content
            pending_ts = ts
        elif role in {"assistant", "bot", "model", "maat ki", "ai"}:
            if skip_next_assistant and "MAAT ChatSearch" in content[:200]:
                skip_next_assistant = False
                continue
            skip_next_assistant = False
            yield turn, pending_ts, pending_user, content
            turn += 1
            pending_user = ""
            pending_ts = fallback_ts
        else:
            yield turn, ts, "", content
            turn += 1
    if pending_user:
        yield turn, pending_ts, pending_user, ""


def _add_doc(docs: list[dict[str, Any]], doc: dict[str, Any], user_text: str, assistant_text: str) -> None:
    combined = "\n".join(
        part
        for part in [
            f"User: {user_text}" if user_text else "",
            f"Assistant: {assistant_text}" if assistant_text else "",
        ]
        if part
    ).strip()
    if not combined:
        return
    docs.append({**doc, "user_text": user_text, "assistant_text": assistant_text, "text": combined})


def _extract_external_docs(path: Path, data: Any) -> list[dict[str, Any]]:
    fallback_ts = _file_timestamp(path)
    chat_name = _chat_name(path, data)
    base = {
        "source": "external",
        "path": str(path),
        "chat_id": None,
        "chat_name": chat_name,
        "file_mtime": path.stat().st_mtime,
    }
    docs: list[dict[str, Any]] = []

    def add(turn: int, ts: str, user_text: str, assistant_text: str) -> None:
        _add_doc(docs, {**base, "turn_index": int(turn), "timestamp": ts or fallback_ts}, user_text, assistant_text)

    if isinstance(data, dict):
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        pairs = data.get("visible") if isinstance(data.get("visible"), list) else data.get("internal")
        if isinstance(pairs, list):
            for turn, ts, user_text, assistant_text in _pairs_from_pair_list(pairs, metadata, fallback_ts):
                add(turn, ts, user_text, assistant_text)
            if docs:
                return docs
        if isinstance(data.get("messages"), list):
            for turn, ts, user_text, assistant_text in _pairs_from_messages(data.get("messages"), fallback_ts):
                add(turn, ts, user_text, assistant_text)
            if docs:
                return docs
        history = data.get("history")
        if isinstance(history, dict):
            subpairs = history.get("visible") if isinstance(history.get("visible"), list) else history.get("internal")
            for turn, ts, user_text, assistant_text in _pairs_from_pair_list(subpairs, metadata, fallback_ts):
                add(turn, ts, user_text, assistant_text)
        elif isinstance(history, list):
            for turn, ts, user_text, assistant_text in _pairs_from_messages(history, fallback_ts):
                add(turn, ts, user_text, assistant_text)
    elif isinstance(data, list):
        if data and all(isinstance(x, (list, tuple)) for x in data[:5]):
            for turn, ts, user_text, assistant_text in _pairs_from_pair_list(data, {}, fallback_ts):
                add(turn, ts, user_text, assistant_text)
        else:
            for turn, ts, user_text, assistant_text in _pairs_from_messages(data, fallback_ts):
                add(turn, ts, user_text, assistant_text)
    return docs


def _parse_iso(value: str) -> float:
    try:
        return dt.datetime.fromisoformat(str(value or "")).timestamp()
    except Exception:
        return 0.0


def _extract_webcore_docs(database: Database, chat: dict[str, Any]) -> list[dict[str, Any]]:
    chat_id = int(chat.get("id") or 0)
    messages = database.chat_messages(chat_id)
    title = str(chat.get("title") or f"Chat {chat_id}")
    path = f"webcore://chat/{chat_id}"
    mtime = _parse_iso(str(chat.get("updated_at") or chat.get("created_at") or "")) or time.time()
    base = {
        "source": "webcore",
        "path": path,
        "chat_id": chat_id,
        "chat_name": f"MAAT Web Core / {title}",
        "file_mtime": mtime,
    }
    docs: list[dict[str, Any]] = []
    turn = 0
    pending_user = ""
    pending_ts = ""
    skip_next_assistant = False
    for item in messages:
        role = str(item.get("role") or "").lower()
        raw = visible_message_text(str(item.get("content") or ""))
        if _is_progress_artifact(raw):
            continue
        content = clean_text(raw)
        if not content:
            continue
        ts = str(item.get("created_at") or "")
        if role == "user":
            if is_chat_search_turn(content):
                pending_user = ""
                skip_next_assistant = True
                continue
            if pending_user:
                _add_doc(docs, {**base, "turn_index": turn, "timestamp": pending_ts}, pending_user, "")
                turn += 1
            pending_user = content
            pending_ts = ts
        elif role == "assistant":
            if skip_next_assistant and "MAAT ChatSearch" in content[:240]:
                skip_next_assistant = False
                continue
            skip_next_assistant = False
            _add_doc(docs, {**base, "turn_index": turn, "timestamp": pending_ts or ts}, pending_user, content)
            turn += 1
            pending_user = ""
            pending_ts = ""
    if pending_user:
        _add_doc(docs, {**base, "turn_index": turn, "timestamp": pending_ts}, pending_user, "")
    return docs


def _delete_path(conn: sqlite3.Connection, path: str) -> None:
    rows = conn.execute("SELECT id FROM chat_docs WHERE path=?", (path,)).fetchall()
    for row in rows:
        try:
            conn.execute("DELETE FROM chat_docs_fts WHERE rowid=?", (row["id"],))
        except sqlite3.OperationalError:
            pass
    conn.execute("DELETE FROM chat_docs WHERE path=?", (path,))


def _delete_indexed_path(conn: sqlite3.Connection, path: str) -> None:
    _delete_path(conn, path)
    conn.execute("DELETE FROM indexed_files WHERE path=?", (path,))


def _insert_docs(conn: sqlite3.Connection, docs: list[dict[str, Any]]) -> int:
    count = 0
    for doc in docs:
        cursor = conn.execute(
            """
            INSERT INTO chat_docs
                (source, path, chat_id, chat_name, turn_index, timestamp, user_text, assistant_text, text, file_mtime)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc["source"],
                doc["path"],
                doc.get("chat_id"),
                doc["chat_name"],
                doc["turn_index"],
                doc["timestamp"],
                doc["user_text"],
                doc["assistant_text"],
                doc["text"],
                doc["file_mtime"],
            ),
        )
        rowid = cursor.lastrowid
        try:
            conn.execute(
                """
                INSERT INTO chat_docs_fts(rowid, text, user_text, assistant_text, chat_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (rowid, doc["text"], doc["user_text"], doc["assistant_text"], doc["chat_name"]),
            )
        except sqlite3.OperationalError:
            pass
        count += 1
    return count


def _index_external_file(conn: sqlite3.Connection, path: Path, force: bool, settings: RuntimeSettings) -> tuple[bool, int]:
    stat = path.stat()
    sp = str(path)
    old = conn.execute("SELECT mtime, size FROM indexed_files WHERE path=?", (sp,)).fetchone()
    if old and not force and float(old["mtime"]) == stat.st_mtime and int(old["size"]) == stat.st_size:
        return False, 0
    _delete_path(conn, sp)
    try:
        docs = _extract_external_docs(path, _read_json(path))
    except Exception as exc:
        _debug(settings, f"external parse failed {path}: {exc}")
        docs = []
    count = _insert_docs(conn, docs)
    conn.execute(
        """
        INSERT INTO indexed_files(path, source, mtime, size, indexed_at, docs)
        VALUES (?, 'external', ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            source=excluded.source, mtime=excluded.mtime, size=excluded.size,
            indexed_at=excluded.indexed_at, docs=excluded.docs
        """,
        (sp, stat.st_mtime, stat.st_size, time.time(), count),
    )
    return True, count


def _index_webcore_chat(conn: sqlite3.Connection, database: Database, chat: dict[str, Any], force: bool) -> tuple[bool, int]:
    chat_id = int(chat.get("id") or 0)
    path = f"webcore://chat/{chat_id}"
    mtime = _parse_iso(str(chat.get("updated_at") or chat.get("created_at") or "")) or 0.0
    size_row = database.connection.execute(
        "SELECT COALESCE(SUM(LENGTH(content)), 0) AS size FROM messages WHERE chat_id = ?",
        (chat_id,),
    ).fetchone()
    size = int(size_row["size"] if size_row else 0)
    old = conn.execute("SELECT mtime, size FROM indexed_files WHERE path=?", (path,)).fetchone()
    if old and not force and float(old["mtime"]) == mtime and int(old["size"]) == size:
        return False, 0
    _delete_path(conn, path)
    docs = _extract_webcore_docs(database, chat)
    count = _insert_docs(conn, docs)
    conn.execute(
        """
        INSERT INTO indexed_files(path, source, mtime, size, indexed_at, docs)
        VALUES (?, 'webcore', ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            source=excluded.source, mtime=excluded.mtime, size=excluded.size,
            indexed_at=excluded.indexed_at, docs=excluded.docs
        """,
        (path, mtime, size, time.time(), count),
    )
    return True, count


def ensure_index(database: Database, settings: RuntimeSettings, force: bool = False) -> dict[str, Any]:
    _ensure_schema()
    now = time.time()
    interval = float(getattr(settings, "chat_search_scan_interval", 45) or 45)
    if not force and SESSION.get("last_scan") and (now - float(SESSION["last_scan"])) < interval:
        return dict(SESSION.get("last_status") or {})

    changed = 0
    docs_changed = 0
    files_seen = 0
    with _connect() as conn:
        seen_webcore: set[str] = set()
        if getattr(settings, "chat_search_include_webcore", True):
            chats = database.connection.execute("SELECT * FROM chats ORDER BY id ASC").fetchall()
            files_seen += len(chats)
            for row in chats:
                chat = dict(row)
                seen_webcore.add(f"webcore://chat/{int(chat.get('id') or 0)}")
                did_change, count = _index_webcore_chat(conn, database, chat, force=force)
                if did_change:
                    changed += 1
                    docs_changed += count
            stale = conn.execute("SELECT path FROM indexed_files WHERE source='webcore'").fetchall()
            for row in stale:
                path = str(row["path"])
                if path not in seen_webcore:
                    _delete_indexed_path(conn, path)
                    changed += 1

        external_files = _iter_external_chat_files(settings)
        files_seen += len(external_files)
        for path in external_files:
            try:
                did_change, count = _index_external_file(conn, path, force=force, settings=settings)
            except Exception as exc:
                _debug(settings, f"index failed {path}: {exc}")
                continue
            if did_change:
                changed += 1
                docs_changed += count

        total_docs = int(conn.execute("SELECT COUNT(*) AS n FROM chat_docs").fetchone()["n"])
        total_files = int(conn.execute("SELECT COUNT(*) AS n FROM indexed_files").fetchone()["n"])

    status = {
        "files_seen": files_seen,
        "files_indexed": total_files,
        "files_changed": changed,
        "docs_total": total_docs,
        "docs_changed": docs_changed,
        "db_path": str(DB_PATH),
        "scanned_at": now,
    }
    SESSION["last_scan"] = now
    SESSION["last_status"] = status
    _debug(settings, f"scan files={files_seen} changed={changed} docs={total_docs}")
    return status


def current_status() -> dict[str, Any]:
    _ensure_schema()
    with _connect() as conn:
        total_docs = int(conn.execute("SELECT COUNT(*) AS n FROM chat_docs").fetchone()["n"])
        total_files = int(conn.execute("SELECT COUNT(*) AS n FROM indexed_files").fetchone()["n"])
    return {
        "files_seen": total_files,
        "files_indexed": total_files,
        "files_changed": 0,
        "docs_total": total_docs,
        "docs_changed": 0,
        "db_path": str(DB_PATH),
        "scanned_at": SESSION.get("last_scan", 0.0),
    }


def _fts_query(query: str) -> str:
    tokens = re.findall(r"[\wÄÖÜäöüß]+", query.lower(), flags=re.UNICODE)
    tokens = [token.strip("_") for token in tokens if len(token.strip("_")) >= 2]
    return " ".join(f"{token}*" for token in tokens[:8])


def _like_query(conn: sqlite3.Connection, query: str, limit: int) -> list[sqlite3.Row]:
    tokens = re.findall(r"[\wÄÖÜäöüß]+", query.lower(), flags=re.UNICODE)
    tokens = [token.strip("_") for token in tokens if token.strip("_")]
    if not tokens:
        return []
    clauses = []
    params: list[str] = []
    for token in tokens[:6]:
        clauses.append("LOWER(text || ' ' || chat_name) LIKE ?")
        params.append(f"%{token.lower()}%")
    sql = f"""
        SELECT *, '' AS snippet
        FROM chat_docs
        WHERE {' AND '.join(clauses)}
        ORDER BY file_mtime DESC, turn_index DESC
        LIMIT ?
    """
    params.append(str(limit))
    return conn.execute(sql, params).fetchall()


def search_chats(database: Database, settings: RuntimeSettings, query: str, limit: int | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    query = (query or "").strip()
    limit = int(limit or getattr(settings, "chat_search_max_results", 6) or 6)
    fetch_limit = max(limit * 4, limit + 8)
    status = ensure_index(database, settings, force=False) if getattr(settings, "chat_search_auto_index", True) else current_status()
    if not query:
        return [], status

    rows: list[sqlite3.Row] = []
    with _connect() as conn:
        fts = _fts_query(query)
        if fts:
            try:
                rows = conn.execute(
                    """
                    SELECT d.*, snippet(chat_docs_fts, 0, '[', ']', ' … ', 18) AS snippet
                    FROM chat_docs_fts
                    JOIN chat_docs d ON d.id = chat_docs_fts.rowid
                    WHERE chat_docs_fts MATCH ?
                    ORDER BY bm25(chat_docs_fts)
                    LIMIT ?
                    """,
                    (fts, fetch_limit),
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
        if not rows:
            rows = _like_query(conn, query, fetch_limit)

    out: list[dict[str, Any]] = []
    for row in rows:
        item = {key: row[key] for key in row.keys()}
        if is_chat_search_turn(item.get("user_text", "")):
            continue
        if _is_progress_artifact(item.get("assistant_text", "")):
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out, status


def extract_query(text: str) -> str | None:
    raw = (text or "").strip()
    patterns = [
        r"^/maat\s+(?:chat\s+)?search\s+(.+)$",
        r"^/maat\s+(?:archive|archiv)\s+search\s+(.+)$",
        r"^/chat\s+search\s+(.+)$",
        r"^(?:finde|such(?:e)?|durchsuche)\s+(?:den\s+)?chats?\s+(?:über|ueber|zu|nach)\s+(.+)$",
        r"^(?:such(?:e)?|durchsuche)\s+im\s+(?:archiv|chat|chatverlauf|chat-archiv)\s+(?:nach\s+)?(.+)$",
        r"^(?:wann|wo)\s+haben\s+wir\s+(?:über|ueber)\s+(.+?)\s+gesprochen\??$",
    ]
    for pattern in patterns:
        match = re.match(pattern, raw, re.IGNORECASE | re.DOTALL)
        if match:
            query = match.group(1).strip(" .?!\"'")
            return query or None
    return None


def _format_bytes(value: int) -> str:
    size = float(value or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} GB"


def _db_size() -> int:
    total = 0
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(DB_PATH) + suffix)
        try:
            total += path.stat().st_size
        except FileNotFoundError:
            pass
    return total


def _format_scan_time(value: Any) -> str:
    try:
        ts = float(value or 0)
    except Exception:
        ts = 0.0
    if ts <= 0:
        return "noch nicht"
    return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def format_search_results(query: str, rows: list[dict[str, Any]], status: dict[str, Any]) -> str:
    lines = [
        "# MAAT ChatSearch",
        "",
        f"Suche: `{query}`",
        f"Index: {int(status.get('docs_total', 0) or 0)} Chat-Turns aus {int(status.get('files_indexed', 0) or 0)} Quellen",
        "",
    ]
    if not rows:
        lines.extend(
            [
                "Keine Treffer gefunden.",
                "",
                "Tipp: Versuch ein einzelnes Schlüsselwort, z.B. `/maat search cci` oder `/maat search musicgen`.",
            ]
        )
        return "\n".join(lines)

    for i, row in enumerate(rows, 1):
        chat = row.get("chat_name") or "Chat"
        ts = row.get("timestamp") or ""
        if not ts and str(row.get("path") or "").startswith("/"):
            ts = _file_timestamp(Path(row.get("path") or ""))
        turn = row.get("turn_index")
        source = row.get("source") or "external"
        lines.append(f"## {i}. {ts or 'ohne Datum'} · {chat} · Turn {turn} · {source}")
        if row.get("user_text"):
            lines.append(f"**User:** {_shorten(row.get('user_text', ''), 240)}")
        if row.get("assistant_text"):
            lines.append(f"**MAAT KI:** {_shorten(row.get('assistant_text', ''), 320)}")
        lines.append(f"`{row.get('path', '')}`")
        lines.append("")
    return "\n".join(lines).strip()


def status_text(database: Database, settings: RuntimeSettings, detailed: bool = False) -> str:
    status = ensure_index(database, settings, force=False)
    roots = _external_roots(settings)
    lines = [
        "# MAAT ChatSearch Stats" if detailed else "# MAAT ChatSearch Status",
        "",
        f"- Aktiv: {'ja' if getattr(settings, 'chat_search_enabled', True) else 'nein'}",
        f"- Web-Core-Chats: {'ja' if getattr(settings, 'chat_search_include_webcore', True) else 'nein'}",
        f"- Auto-Index: {'ja' if getattr(settings, 'chat_search_auto_index', True) else 'nein'}",
        f"- Dateien/Chats im Index: {status.get('files_indexed', 0)}",
        f"- Chat-Turns im Index: {status.get('docs_total', 0)}",
        f"- Geänderte Quellen beim letzten Scan: {status.get('files_changed', 0)}",
        f"- Letzter Scan: {_format_scan_time(status.get('scanned_at'))}",
        f"- DB-Größe: {_format_bytes(_db_size())}",
        f"- DB: `{DB_PATH}`",
    ]
    if detailed:
        lines.append("")
        lines.append("## Externe Scan-Wurzeln")
        if roots:
            for root in roots:
                lines.append(f"- `{root}`")
        else:
            lines.append("- Keine externen Log-Ordner gefunden.")
    return "\n".join(lines)


def command_chat_search(database: Database, settings: RuntimeSettings, args: list[str]) -> str:
    if not args:
        return (
            "# MAAT ChatSearch\n\n"
            "Beispiele:\n"
            "- `/maat search musicgen`\n"
            "- `/maat search \"MAAT Pinball\"`\n"
            "- `/maat search stats`\n"
            "- `/maat search rebuild`\n"
            "- `finde chat über CCI`\n"
            "- `suche im archiv nach projekt`"
        )
    raw = str(args[0]).lower()
    if raw in {"on", "off"}:
        settings.chat_search_enabled = raw == "on"
        return f"MAAT ChatSearch {'aktiviert' if settings.chat_search_enabled else 'deaktiviert'}."
    if raw == "auto" and len(args) >= 2:
        settings.chat_search_auto_index = str(args[1]).lower() in {"on", "true", "1", "ja", "an"}
        return f"ChatSearch Auto-Index {'an' if settings.chat_search_auto_index else 'aus'}."
    if raw == "debug" and len(args) >= 2:
        settings.chat_search_debug = str(args[1]).lower() in {"on", "true", "1", "ja", "an"}
        return f"ChatSearch Debug {'an' if settings.chat_search_debug else 'aus'}."
    if raw in {"webcore", "web"} and len(args) >= 2:
        settings.chat_search_include_webcore = str(args[1]).lower() in {"on", "true", "1", "ja", "an"}
        return f"Web-Core-Chats im ChatSearch {'an' if settings.chat_search_include_webcore else 'aus'}."
    if raw == "limit" and len(args) >= 2:
        try:
            settings.chat_search_max_results = max(1, min(30, int(args[1])))
        except (TypeError, ValueError):
            return "Usage: /maat search limit <1-30>"
        return f"ChatSearch Trefferlimit={settings.chat_search_max_results} gespeichert."
    if raw in {"status"}:
        return status_text(database, settings, detailed=False)
    if raw in {"stats", "statistik"}:
        return status_text(database, settings, detailed=True)
    if raw in {"reindex", "rebuild", "index"}:
        status = ensure_index(database, settings, force=True)
        return (
            "# MAAT ChatSearch Rebuild\n\n"
            f"Index erneuert: {status.get('docs_total', 0)} Chat-Turns aus {status.get('files_indexed', 0)} Quellen."
        )

    query = " ".join(args).strip()
    rows, status = search_chats(database, settings, query)
    return format_search_results(query, rows, status)


def direct_chat_search_answer(database: Database, settings: RuntimeSettings, user_text: str) -> str | None:
    if not getattr(settings, "chat_search_enabled", True):
        return None
    query = extract_query(user_text)
    if not query:
        return None
    rows, status = search_chats(database, settings, query)
    return format_search_results(query, rows, status)
