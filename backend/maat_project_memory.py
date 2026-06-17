from __future__ import annotations

import hashlib
import re
import time
import unicodedata
from typing import Any

from .database import Database, now_iso


PROJECT_OPEN = "[PROJECT_MEMORY]"
PROJECT_CLOSE = "[/PROJECT_MEMORY]"

ENTRY_TYPES = ["context", "formula", "insight", "experiment", "paper", "decision", "bug", "todo"]
PROJECT_STATUSES = ["aktiv", "paused", "archiv", "draft"]


def _fold(text: Any) -> str:
    value = unicodedata.normalize("NFKD", str(text or "").lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value).strip()


def _split_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[,;\n]+", str(value or ""))
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        clean = str(item or "").strip()
        key = _fold(clean)
        if clean and key not in seen:
            seen.add(key)
            out.append(clean)
    return out


def _join_list(value: Any) -> str:
    return ", ".join(_split_list(value))


def _new_id(prefix: str, text: str = "") -> str:
    seed = f"{prefix}:{text}:{time.time_ns()}"
    return hashlib.sha1(seed.encode("utf-8", "ignore")).hexdigest()[:12]


def _clip(text: Any, limit: int) -> str:
    clean = str(text or "").strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 24)].rstrip() + "\n[...gekuerzt...]"


def _project_row(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["tags"] = _split_list(item.get("tags"))
    item["recall_triggers"] = _split_list(item.get("recall_triggers"))
    return item


def initialize_project_memory(database: Database) -> None:
    database.connection.execute(
        """
        CREATE TABLE IF NOT EXISTS maat_projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            tags TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            context TEXT NOT NULL DEFAULT '',
            version TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'aktiv',
            recall_triggers TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    database.connection.execute(
        """
        CREATE TABLE IF NOT EXISTS maat_project_formulas (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            formula TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES maat_projects(id) ON DELETE CASCADE
        )
        """
    )
    database.connection.execute(
        """
        CREATE TABLE IF NOT EXISTS maat_project_papers (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            ref TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES maat_projects(id) ON DELETE CASCADE
        )
        """
    )
    database.connection.execute(
        """
        CREATE TABLE IF NOT EXISTS maat_project_entries (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            entry_type TEXT NOT NULL DEFAULT 'context',
            text TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES maat_projects(id) ON DELETE CASCADE
        )
        """
    )
    database.connection.commit()


def list_projects(database: Database) -> list[dict[str, Any]]:
    rows = database.connection.execute(
        """
        SELECT p.*,
            (SELECT COUNT(*) FROM maat_project_formulas f WHERE f.project_id = p.id) AS formula_count,
            (SELECT COUNT(*) FROM maat_project_papers pp WHERE pp.project_id = p.id) AS paper_count,
            (SELECT COUNT(*) FROM maat_project_entries e WHERE e.project_id = p.id) AS entry_count
        FROM maat_projects p
        ORDER BY p.updated_at DESC, p.name COLLATE NOCASE
        """
    ).fetchall()
    return [_project_row(row) for row in rows]


def _find_project(database: Database, name_or_id: str) -> dict[str, Any] | None:
    probe = str(name_or_id or "").strip()
    if not probe:
        return None
    row = database.connection.execute("SELECT * FROM maat_projects WHERE id = ?", (probe,)).fetchone()
    if row:
        return _project_row(row)
    row = database.connection.execute("SELECT * FROM maat_projects WHERE lower(name) = lower(?)", (probe,)).fetchone()
    if row:
        return _project_row(row)
    row = database.connection.execute("SELECT * FROM maat_projects WHERE lower(name) LIKE lower(?)", (f"%{probe}%",)).fetchone()
    return _project_row(row) if row else None


def _children(database: Database, project_id: str) -> dict[str, list[dict[str, Any]]]:
    formulas = [
        dict(row)
        for row in database.connection.execute(
            "SELECT * FROM maat_project_formulas WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    ]
    papers = [
        dict(row)
        for row in database.connection.execute(
            "SELECT * FROM maat_project_papers WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    ]
    entries = [
        {**dict(row), "tags": _split_list(row["tags"])}
        for row in database.connection.execute(
            "SELECT * FROM maat_project_entries WHERE project_id = ? ORDER BY created_at DESC LIMIT 200",
            (project_id,),
        ).fetchall()
    ]
    return {"formulas": formulas, "papers": papers, "entries": entries}


def get_project(database: Database, name_or_id: str) -> dict[str, Any] | None:
    project = _find_project(database, name_or_id)
    if not project:
        return None
    project.update(_children(database, project["id"]))
    return project


def upsert_project(database: Database, payload: dict[str, Any]) -> dict[str, Any]:
    name = " ".join(str(payload.get("name") or "").strip().split())
    if not name:
        raise ValueError("Projektname fehlt.")
    now = now_iso()
    existing = _find_project(database, str(payload.get("id") or name))
    project_id = existing["id"] if existing else _new_id("project", name)
    created_at = existing["created_at"] if existing else now
    tags = _join_list(payload.get("tags"))
    triggers = _join_list(payload.get("recall_triggers") or payload.get("triggers") or tags)
    status = str(payload.get("status") or "aktiv").strip() or "aktiv"
    database.connection.execute(
        """
        INSERT INTO maat_projects(id, name, tags, description, context, version, status, recall_triggers, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            tags = excluded.tags,
            description = excluded.description,
            context = excluded.context,
            version = excluded.version,
            status = excluded.status,
            recall_triggers = excluded.recall_triggers,
            updated_at = excluded.updated_at
        """,
        (
            project_id,
            name,
            tags,
            str(payload.get("description") or "").strip(),
            str(payload.get("context") or "").strip(),
            str(payload.get("version") or "").strip(),
            status,
            triggers,
            created_at,
            now,
        ),
    )
    database.connection.commit()
    return get_project(database, project_id) or {}


def add_formula(database: Database, project_name: str, name: str, formula: str, description: str = "") -> dict[str, Any]:
    project = _find_project(database, project_name)
    if not project:
        raise ValueError("Projekt nicht gefunden.")
    formula_text = str(formula or "").strip()
    if not formula_text:
        raise ValueError("Formel darf nicht leer sein.")
    formula_name = str(name or "").strip() or f"Formel {int(time.time())}"
    item_id = _new_id("formula", formula_name + formula_text)
    database.connection.execute(
        """
        INSERT INTO maat_project_formulas(id, project_id, name, formula, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (item_id, project["id"], formula_name, formula_text, str(description or "").strip(), now_iso()),
    )
    database.connection.execute("UPDATE maat_projects SET updated_at = ? WHERE id = ?", (now_iso(), project["id"]))
    database.connection.commit()
    return dict(database.connection.execute("SELECT * FROM maat_project_formulas WHERE id = ?", (item_id,)).fetchone())


def add_paper(database: Database, project_name: str, title: str, ref: str = "", notes: str = "") -> dict[str, Any]:
    project = _find_project(database, project_name)
    if not project:
        raise ValueError("Projekt nicht gefunden.")
    clean_title = str(title or "").strip()
    if not clean_title:
        raise ValueError("Paper-Titel darf nicht leer sein.")
    item_id = _new_id("paper", clean_title)
    database.connection.execute(
        """
        INSERT INTO maat_project_papers(id, project_id, title, ref, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (item_id, project["id"], clean_title, str(ref or "").strip(), str(notes or "").strip(), now_iso()),
    )
    database.connection.execute("UPDATE maat_projects SET updated_at = ? WHERE id = ?", (now_iso(), project["id"]))
    database.connection.commit()
    return dict(database.connection.execute("SELECT * FROM maat_project_papers WHERE id = ?", (item_id,)).fetchone())


def add_entry(database: Database, project_name: str, entry_type: str, text: str, tags: Any = "") -> dict[str, Any]:
    project = _find_project(database, project_name)
    if not project:
        raise ValueError("Projekt nicht gefunden.")
    clean = str(text or "").strip()
    if not clean:
        raise ValueError("Eintrag darf nicht leer sein.")
    kind = str(entry_type or "context").strip()
    if kind not in ENTRY_TYPES:
        kind = "context"
    item_id = _new_id("entry", clean)
    database.connection.execute(
        """
        INSERT INTO maat_project_entries(id, project_id, entry_type, text, tags, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (item_id, project["id"], kind, clean, _join_list(tags), now_iso()),
    )
    database.connection.execute("UPDATE maat_projects SET updated_at = ? WHERE id = ?", (now_iso(), project["id"]))
    database.connection.commit()
    return dict(database.connection.execute("SELECT * FROM maat_project_entries WHERE id = ?", (item_id,)).fetchone())


def delete_child(database: Database, kind: str, child_id: str) -> bool:
    table = {
        "formula": "maat_project_formulas",
        "paper": "maat_project_papers",
        "entry": "maat_project_entries",
    }.get(str(kind or ""))
    if not table:
        raise ValueError("Unbekannter Typ.")
    row = database.connection.execute(f"SELECT project_id FROM {table} WHERE id = ?", (child_id,)).fetchone()
    if not row:
        return False
    database.connection.execute(f"DELETE FROM {table} WHERE id = ?", (child_id,))
    database.connection.execute("UPDATE maat_projects SET updated_at = ? WHERE id = ?", (now_iso(), row["project_id"]))
    database.connection.commit()
    return True


def _score_project(project: dict[str, Any], query: str, child_text: str = "") -> float:
    q = _fold(query)
    if not q:
        return 0.0
    score = 0.0
    name = _fold(project.get("name"))
    if q == name:
        score += 6.0
    elif q in name:
        score += 3.0
    for trigger in _split_list(project.get("recall_triggers")):
        t = _fold(trigger)
        if not t:
            continue
        if re.search(rf"\b{re.escape(t)}\b", q):
            score += 4.0
        elif t in q:
            score += 2.5
    for tag in _split_list(project.get("tags")):
        t = _fold(tag)
        if t and re.search(rf"\b{re.escape(t)}\b", q):
            score += 1.6
    blob = _fold(
        " ".join(
            [
                str(project.get("description") or ""),
                str(project.get("context") or "")[:1600],
                child_text,
            ]
        )
    )
    for word in re.findall(r"[a-z0-9_]{3,}", q)[:14]:
        if re.search(rf"\b{re.escape(word)}\b", blob):
            score += 0.55
    return score


def search_projects(database: Database, query: str, limit: int = 2) -> list[dict[str, Any]]:
    rows = database.connection.execute("SELECT * FROM maat_projects").fetchall()
    hits: list[dict[str, Any]] = []
    for row in rows:
        project = _project_row(row)
        children = _children(database, project["id"])
        child_text = " ".join(
            [
                " ".join(f"{f.get('name', '')} {f.get('formula', '')}" for f in children["formulas"][:8]),
                " ".join(f"{p.get('title', '')} {p.get('ref', '')}" for p in children["papers"][:8]),
                " ".join(e.get("text", "") for e in children["entries"][:12]),
            ]
        )
        score = _score_project(project, query, child_text)
        if score > 0:
            full = {**project, **children, "_score": round(score, 3)}
            hits.append(full)
    hits.sort(key=lambda item: (float(item.get("_score") or 0), str(item.get("updated_at") or "")), reverse=True)
    return hits[: max(0, int(limit or 2))]


def _format_project_block(projects: list[dict[str, Any]], max_chars: int) -> str:
    if not projects:
        return ""
    chunks = [PROJECT_OPEN]
    for idx, project in enumerate(projects, start=1):
        chunks.append(f"Projekt {idx}: {project.get('name', '')}")
        if project.get("version"):
            chunks.append(f"Version: {project.get('version')}")
        chunks.append(f"Status: {project.get('status', 'aktiv')}")
        if project.get("tags"):
            chunks.append(f"Tags: {_join_list(project.get('tags'))}")
        if project.get("description"):
            chunks.append(f"Beschreibung: {project.get('description')}")
        if project.get("context"):
            chunks.append("Kontext:")
            chunks.append(_clip(project.get("context"), 900))
        formulas = project.get("formulas") or []
        if formulas:
            chunks.append("Formeln:")
            for formula in formulas[:6]:
                desc = f" - {formula.get('description')}" if formula.get("description") else ""
                chunks.append(f"- {formula.get('name')}: {formula.get('formula')}{desc}")
        papers = project.get("papers") or []
        if papers:
            chunks.append("Papers:")
            for paper in papers[:6]:
                ref = f" ({paper.get('ref')})" if paper.get("ref") else ""
                note = f" - {paper.get('notes')}" if paper.get("notes") else ""
                chunks.append(f"- {paper.get('title')}{ref}{note}")
        entries = project.get("entries") or []
        if entries:
            chunks.append("Letzte Projekt-Eintraege:")
            for entry in entries[:5]:
                chunks.append(f"- [{entry.get('entry_type')}] {entry.get('text')}")
        chunks.append("")
    chunks.append(PROJECT_CLOSE)
    return _clip("\n".join(chunks).strip(), max_chars)


def build_project_prompt(database: Database, settings: Any, user_input: str) -> tuple[str, dict[str, Any]]:
    if not bool(getattr(settings, "project_memory_enabled", True)):
        return "", {"enabled": False, "hits": []}
    query = str(user_input or "").strip()
    if not query or query.startswith("/"):
        return "", {"enabled": True, "hits": []}
    top_k = max(0, min(5, int(getattr(settings, "project_memory_top_k", 2) or 2)))
    if top_k <= 0:
        return "", {"enabled": True, "hits": []}
    hits = search_projects(database, query, top_k)
    max_chars = max(800, min(8000, int(getattr(settings, "project_memory_max_chars", 2600) or 2600)))
    block = _format_project_block(hits, max_chars)
    info = {
        "enabled": True,
        "hits": [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "score": item.get("_score"),
                "status": item.get("status"),
                "tags": item.get("tags") or [],
            }
            for item in hits
        ],
        "block_chars": len(block),
    }
    return ("\n\n" + block + "\n" if block else ""), info


def format_project_markdown(database: Database, name_or_id: str = "") -> str:
    if not name_or_id:
        projects = list_projects(database)
        if not projects:
            return "Noch keine Projekte angelegt."
        lines = ["## MAAT Projects", ""]
        for project in projects:
            tags = _join_list(project.get("tags")) or "-"
            version = f" v{project.get('version')}" if project.get("version") else ""
            lines.append(
                f"- **{project.get('name')}{version}** [{project.get('status', 'aktiv')}] "
                f"`{tags}` · Formeln {project.get('formula_count', 0)} · Papers {project.get('paper_count', 0)} · Eintraege {project.get('entry_count', 0)}"
            )
        return "\n".join(lines)
    project = get_project(database, name_or_id)
    if not project:
        return f"Projekt nicht gefunden: `{name_or_id}`"
    lines = [
        f"## {project.get('name', 'Unbenannt')}",
        f"- Status: `{project.get('status', 'aktiv')}`",
        f"- Version: `{project.get('version') or '-'}`",
        f"- Tags: `{_join_list(project.get('tags')) or '-'}`",
        f"- Trigger: `{_join_list(project.get('recall_triggers')) or '-'}`",
        f"- Letzte Aenderung: `{project.get('updated_at', '-')}`",
    ]
    if project.get("description"):
        lines += ["", "### Kurzbeschreibung", str(project.get("description") or "")]
    if project.get("context"):
        lines += ["", "### Kontext", _clip(project.get("context"), 1800)]
    if project.get("formulas"):
        lines += ["", "### Formeln"]
        for formula in project["formulas"]:
            formula_body = str(formula.get("formula") or "").replace("```", "`\u200b``")
            lines.append(
                f"**{formula.get('name', '')}**"
                + (f" - {formula.get('description')}" if formula.get("description") else "")
                + f"\n\n```text\n{formula_body}\n```"
                + f"\nID: `{formula.get('id')}`"
            )
    if project.get("papers"):
        lines += ["", "### Papers"]
        for paper in project["papers"]:
            ref = f" `{paper.get('ref')}`" if paper.get("ref") else ""
            note = f" - {paper.get('notes')}" if paper.get("notes") else ""
            lines.append(f"- {paper.get('title', '')}{ref}{note}  \n  ID: `{paper.get('id')}`")
    if project.get("entries"):
        lines += ["", "### Letzte Eintraege"]
        for entry in project["entries"][:12]:
            tags = f" `{_join_list(entry.get('tags'))}`" if entry.get("tags") else ""
            lines.append(f"- [{entry.get('entry_type', 'context')}] {entry.get('text', '')}{tags}  \n  ID: `{entry.get('id')}`")
    return "\n".join(lines)


def command_project(database: Database, settings: Any, args: list[str]) -> str:
    if not args or args[0] in {"list", "projects"}:
        return format_project_markdown(database)
    raw = str(args[0]).lower()
    if raw in {"on", "off"}:
        settings.project_memory_enabled = raw == "on"
        return f"MAAT Project Memory {'aktiviert' if settings.project_memory_enabled else 'deaktiviert'}."
    if raw == "debug":
        if len(args) >= 2:
            settings.project_memory_debug = str(args[1]).lower() in {"on", "an", "1", "true", "ja"}
        else:
            settings.project_memory_debug = not bool(getattr(settings, "project_memory_debug", False))
        return f"Project Memory Debug {'an' if settings.project_memory_debug else 'aus'}."
    if raw == "status":
        return (
            "MAAT Project Memory Status:\n"
            f"- enabled: {getattr(settings, 'project_memory_enabled', True)}\n"
            f"- debug: {getattr(settings, 'project_memory_debug', False)}\n"
            f"- top_k: {getattr(settings, 'project_memory_top_k', 2)}\n"
            f"- max_chars: {getattr(settings, 'project_memory_max_chars', 2600)}\n"
            f"- projects: {len(list_projects(database))}"
        )
    if raw == "top" and len(args) >= 2:
        settings.project_memory_top_k = max(0, min(5, int(args[1])))
        return f"Project-Memory Top-K: {settings.project_memory_top_k}"
    if raw == "show":
        return format_project_markdown(database, " ".join(args[1:]).strip())
    if raw == "search":
        query = " ".join(args[1:]).strip()
        hits = search_projects(database, query, 5)
        if not hits:
            return "Keine Projekte gefunden."
        return "Project-Memory Treffer:\n" + "\n".join(f"- {item.get('name')} score={item.get('_score')}" for item in hits)
    joined = " ".join(args[1:]).strip()
    if raw == "add":
        parts = [part.strip() for part in joined.split("|", 2)]
        if len(parts) < 3:
            return "Usage: `/maat project add <name>|<tags>|<beschreibung>`"
        project = upsert_project(database, {"name": parts[0], "tags": parts[1], "description": parts[2], "recall_triggers": parts[1]})
        return f"Projekt gespeichert: {project.get('name')}"
    if raw == "save":
        parts = [part.strip() for part in joined.split("|", 2)]
        if len(parts) < 3:
            return "Usage: `/maat project save <projekt>|<typ>|<text>`"
        item = add_entry(database, parts[0], parts[1], parts[2])
        return f"Eintrag gespeichert: {item.get('entry_type')}"
    if raw == "formula" and len(args) >= 3 and args[1] == "add":
        parts = [part.strip() for part in " ".join(args[2:]).split("|", 3)]
        if len(parts) < 3:
            return "Usage: `/maat project formula add <projekt>|<name>|<formel>|<beschreibung>`"
        item = add_formula(database, parts[0], parts[1], parts[2], parts[3] if len(parts) > 3 else "")
        return f"Formel gespeichert: {item.get('name')}"
    if raw == "paper" and len(args) >= 3 and args[1] == "add":
        parts = [part.strip() for part in " ".join(args[2:]).split("|", 3)]
        if len(parts) < 2:
            return "Usage: `/maat project paper add <projekt>|<titel>|<ref>|<notizen>`"
        item = add_paper(database, parts[0], parts[1], parts[2] if len(parts) > 2 else "", parts[3] if len(parts) > 3 else "")
        return f"Paper gespeichert: {item.get('title')}"
    return (
        "MAAT Project Memory Befehle:\n"
        "- `/maat project`\n"
        "- `/maat project on|off`\n"
        "- `/maat project debug [on|off]`\n"
        "- `/maat project status`\n"
        "- `/maat project top <0-5>`\n"
        "- `/maat project show <name>`\n"
        "- `/maat project search <query>`\n"
        "- `/maat project add <name>|<tags>|<beschreibung>`\n"
        "- `/maat project save <projekt>|<typ>|<text>`\n"
        "- `/maat project formula add <projekt>|<name>|<formel>|<beschreibung>`\n"
        "- `/maat project paper add <projekt>|<titel>|<ref>|<notizen>`"
    )


def project_state(database: Database, settings: Any, selected: str = "") -> dict[str, Any]:
    projects = list_projects(database)
    target = selected or (projects[0]["id"] if projects else "")
    project = get_project(database, target) if target else None
    return {
        "enabled": bool(getattr(settings, "project_memory_enabled", True)),
        "debug": bool(getattr(settings, "project_memory_debug", False)),
        "top_k": int(getattr(settings, "project_memory_top_k", 2) or 2),
        "max_chars": int(getattr(settings, "project_memory_max_chars", 2600) or 2600),
        "projects": projects,
        "selected": project,
        "entry_types": ENTRY_TYPES,
        "statuses": PROJECT_STATUSES,
    }
