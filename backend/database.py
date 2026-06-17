from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import DATABASE_PATH, ensure_directories


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def visible_message_text(content: str) -> str:
    def replacement(match: re.Match[str]) -> str:
        attrs = dict(re.findall(r'([a-z0-9_-]+)="([^"]*)"', match.group(1), flags=re.I))
        name = attrs.get("name") or "Textanhang"
        return f" Anhang: {name} "

    return re.sub(
        r"\[MAAT_ATTACHMENT([^\]]*)\]\s*[\s\S]*?\s*\[/MAAT_ATTACHMENT\]",
        replacement,
        str(content or ""),
        flags=re.I,
    )


class Database:
    def __init__(self, path: Path = DATABASE_PATH):
        ensure_directories()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                title_locked INTEGER NOT NULL DEFAULT 0,
                summary_short TEXT NOT NULL DEFAULT '',
                summary_long TEXT NOT NULL DEFAULT '',
                summary_updated_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._ensure_column("chats", "title_locked", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("chats", "summary_short", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("chats", "summary_long", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("chats", "summary_updated_at", "TEXT NOT NULL DEFAULT ''")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS plugin_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                plugin_id TEXT,
                event_type TEXT,
                payload TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = {
            str(row["name"])
            for row in self.connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            self.connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def create_chat(self, title: str = "Neuer Chat") -> int:
        timestamp = now_iso()
        cursor = self.connection.execute(
            "INSERT INTO chats(title, created_at, updated_at) VALUES (?, ?, ?)",
            (title, timestamp, timestamp),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def get_or_create_chat(self, chat_id: int | None) -> int:
        if chat_id:
            row = self.connection.execute("SELECT id FROM chats WHERE id = ?", (chat_id,)).fetchone()
            if row:
                return int(row["id"])
        return self.create_chat()

    def add_message(self, chat_id: int, role: str, content: str) -> int:
        timestamp = now_iso()
        cursor = self.connection.execute(
            "INSERT INTO messages(chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, timestamp),
        )
        if self._chat_title_locked(chat_id):
            self.connection.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (timestamp, chat_id))
        else:
            title = self._title_from_first_user_message(chat_id)
            self.connection.execute(
                "UPDATE chats SET title = ?, updated_at = ? WHERE id = ?",
                (title, timestamp, chat_id),
            )
        self.connection.commit()
        return int(cursor.lastrowid)

    def rename_chat(self, chat_id: int, title: str) -> bool:
        clean_title = " ".join(str(title or "").strip().split())[:90]
        if not clean_title:
            return False
        cursor = self.connection.execute(
            "UPDATE chats SET title = ?, title_locked = 1, updated_at = ? WHERE id = ?",
            (clean_title, now_iso(), chat_id),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def update_chat_summary(
        self,
        chat_id: int,
        summary_short: str,
        summary_long: str,
        auto_title: str = "",
    ) -> dict[str, Any] | None:
        timestamp = now_iso()
        clean_short = str(summary_short or "").strip()[:900]
        clean_long = str(summary_long or "").strip()[:6000]
        clean_title = " ".join(str(auto_title or "").strip().split())[:90]
        if not clean_short and not clean_long and not clean_title:
            return self.chat(chat_id)

        if clean_title and not self._chat_title_locked(chat_id):
            self.connection.execute(
                """
                UPDATE chats
                SET title = ?, summary_short = ?, summary_long = ?, summary_updated_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (clean_title, clean_short, clean_long, timestamp, timestamp, chat_id),
            )
        else:
            self.connection.execute(
                """
                UPDATE chats
                SET summary_short = ?, summary_long = ?, summary_updated_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (clean_short, clean_long, timestamp, timestamp, chat_id),
            )
        self.connection.commit()
        return self.chat(chat_id)

    def delete_chat(self, chat_id: int) -> bool:
        self.connection.execute("DELETE FROM plugin_events WHERE chat_id = ?", (chat_id,))
        self.connection.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        cursor = self.connection.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        self.connection.commit()
        return cursor.rowcount > 0

    def recent_messages(self, chat_id: int, limit: int = 12) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, limit),
        ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def chat(self, chat_id: int) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
        return dict(row) if row else None

    def chat_messages(self, chat_id: int) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY id ASC
            """,
            (chat_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_chats(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
                c.*,
                (SELECT COUNT(*) FROM messages m WHERE m.chat_id = c.id) AS message_count,
                COALESCE(
                    NULLIF(c.summary_short, ''),
                    (
                        SELECT m.content
                        FROM messages m
                        WHERE m.chat_id = c.id
                        ORDER BY m.id DESC
                        LIMIT 1
                    )
                ) AS preview
            FROM chats c
            ORDER BY c.updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def stats(self) -> dict[str, int]:
        chats = self.connection.execute("SELECT COUNT(*) AS c FROM chats").fetchone()["c"]
        messages = self.connection.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]
        return {"chats": int(chats), "messages": int(messages)}

    def log_plugin_event(
        self,
        chat_id: int | None,
        plugin_id: str,
        event_type: str,
        payload: str,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO plugin_events(chat_id, plugin_id, event_type, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, plugin_id, event_type, payload, now_iso()),
        )
        self.connection.commit()

    def _title_from_first_user_message(self, chat_id: int) -> str:
        row = self.connection.execute(
            """
            SELECT content FROM messages
            WHERE chat_id = ? AND role = 'user'
            ORDER BY id ASC LIMIT 1
            """,
            (chat_id,),
        ).fetchone()
        if not row:
            return "Neuer Chat"
        words = visible_message_text(row["content"]).strip().replace("\n", " ").split()
        return " ".join(words[:7])[:70] or "Neuer Chat"

    def _chat_title_locked(self, chat_id: int) -> bool:
        row = self.connection.execute("SELECT title_locked FROM chats WHERE id = ?", (chat_id,)).fetchone()
        return bool(row and row["title_locked"])
