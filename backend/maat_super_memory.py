from __future__ import annotations

import html
import json
import math
import re
import sqlite3
import time
from datetime import datetime, timedelta
from hashlib import md5
from typing import Any

from .database import Database, now_iso
from .maat_memory_archive import (
    archive_old_memories,
    archive_stats,
    initialize_memory_archive,
    recall_archive_for_window,
    recall_archived_sources_for_window,
)
from .maat_memory_dreaming import run_memory_dreaming


DEFAULT_PERSON_NAMES = (
    "Alice, Bob, Charlie"
)

WORKING_MEMORY: list[dict[str, Any]] = []
MAX_WORKING = 16

CATEGORY_KEYWORDS = {
    "beziehung": ["freund", "familie", "partner", "liebe", "vertrauen", "nähe", "oma", "opa", "bruder"],
    "technik": ["ki", "ai", "modell", "python", "gpu", "code", "plugin", "modul", "llama", "gguf"],
    "emotion": ["glücklich", "traurig", "angst", "wut", "freude", "hoffnung", "fühle", "vermisse"],
    "meta": ["bewusstsein", "philosophie", "maat", "harmonie", "balance", "universum"],
    "projekt": ["maat-ki", "github", "paper", "theorie", "veröffentlich", "research", "zenodo", "arxiv"],
    "wissen": ["was ist", "erkläre", "definition", "bedeutet", "warum", "wie funktioniert"],
}

MEMORY_TYPE_MARKERS = {
    "identity": ["ich heiße", "ich heisse", "mein name", "aktueller user", "aktueller nutzer", "ich bin der user", "ich bin der nutzer"],
    "preference": ["ich mag", "ich möchte", "ich will", "gefällt mir", "lieber", "bevorzuge"],
    "project": ["projekt", "paper", "maat", "plugin", "web core", "theorie", "repo", "github"],
    "decision": ["entscheidung", "wir machen", "wir bauen", "festgelegt", "beschlossen"],
    "relationship": ["freund", "bruder", "schwester", "oma", "opa", "tante", "onkel", "familie"],
    "technical": ["python", "code", "fehler", "script", "loader", "llama", "gguf", "api"],
    "temporary": ["heute", "morgen", "mittag", "termin", "gleich", "später", "spaeter"],
}

TYPE_BONUS = {
    "identity": 0.16,
    "preference": 0.14,
    "project": 0.12,
    "decision": 0.12,
    "relationship": 0.12,
    "technical": 0.08,
    "temporary": 0.03,
    "fact": 0.04,
}

SAVE_KV_RE = re.compile(
    r"(?is)\b(memory|keywords|tags|always|type|memory_type|field|maat_field|priority)\s*=\s*(.*?)"
    r"(?=(?:,\s*|\s+)(?:memory|keywords|tags|always|type|memory_type|field|maat_field|priority)\s*=|$)"
)
SAVE_START_RE = re.compile(r"(?is)\bsave\s*:\s*")

MANUAL_SAVE_PATTERNS = [
    re.compile(r"^\s*remember\s*:\s*(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*remember\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*merke\s+dir\s*:\s*(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*merke\s+dir\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*merk\s+dir\s*:\s*(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*merk\s+dir\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*speichere\s*:\s*(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*speichere\s+(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*notiere\s*:\s*(.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*notiere\s+(.+)$", re.IGNORECASE | re.DOTALL),
]

INTERNAL_MARKERS = (
    "[MAAT_INTERNAL",
    "[MAAT_STYLE",
    "[MAAT_EMOTION",
    "[MAAT_THINKING",
    "[MAAT_MEMORY",
    "[MAAT_CHAT_SUMMARY",
    "MAAT Emotion guidance",
    "MAAT Style guidance",
    "Here's a thinking process",
)

FREE_THINKING_START_RE = re.compile(
    r"^\s*(?:"
    r"here(?:'|’)?s a thinking process:|"
    r"thinking process:|"
    r"analy[sz]e user input:|"
    r"denkprozess:|"
    r"gedankenprozess:|"
    r"the user\b|"
    r"user said:|"
    r"the prompt\b|"
    r"the system instructions\b|"
    r"i need to\b|"
    r"we need to\b|"
    r"apply maat principles:"
    r")",
    re.IGNORECASE,
)

INTERNAL_THINKING_HINT_RE = re.compile(
    r"(?:"
    r"self[- ]correction|"
    r"refinement during|"
    r"output generation|"
    r"proceeds?\.?|"
    r"all constraints met|"
    r"no internal tags visible|"
    r"draft(?:ing)?|"
    r"plan:|"
    r"response plan|"
    r"i'?ll\s+(?:keep|use|answer|write|provide|create)|"
    r"the prompt says|"
    r"matches the final response|"
    r"ready\.?\s*$"
    r")",
    re.IGNORECASE | re.MULTILINE,
)

FINAL_ANSWER_LABEL_RE = re.compile(
    r"(?im)^\s*(?:"
    r"\[(?:antwort|final|final answer|output)\]|"
    r"(?:final output generation|final output|final answer|antwort|output)\s*:"
    r")\s*"
)

FINAL_ANSWER_START_RE = re.compile(
    r"(?im)^\s*(?P<answer>"
    r"gern geschehen[!,.]?|"
    r"gern[!,.]?|"
    r"gerne[!,.]?|"
    r"sehr gern[!,.]?|"
    r"kein problem[!,.]?|"
    r"hallo\b|"
    r"hi\b|"
    r"hey\b|"
    r"klar[!,.]?|"
    r"alles klar[!,.]?|"
    r"natürlich[!,.]?|"
    r"ja[!,.]?|"
    r"nein[!,.]?|"
    r"gut[!,.]?|"
    r"passt[!,.]?|"
    r"fertig[!,.]?|"
    r"hier\b|"
    r"hier\s+(?:ist|kommt|die|der|das)\b|"
    r"das\s+(?:ist|passt|geht|klingt)\b|"
    r"ich\s+(?:habe|würde|sehe|denke)\b"
    r")",
)

IMAGE_HELPER_MARKERS = (
    "der nutzer möchte ein bild erzeugen",
    "der nutzer moechte ein bild erzeugen",
    "lokale image-ai-erweiterung",
    "maat-image-chat-card",
    "bild wird erstellt",
)


def initialize_super_memory(database: Database) -> None:
    conn = database.connection
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS supermem_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            layer TEXT NOT NULL,
            ts REAL NOT NULL,
            role TEXT NOT NULL,
            author_user TEXT DEFAULT '',
            content TEXT NOT NULL,
            compressed TEXT DEFAULT '',
            keywords TEXT DEFAULT '',
            category TEXT DEFAULT 'allgemein',
            memory_type TEXT DEFAULT 'fact',
            maat_field TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            priority REAL DEFAULT 0.50,
            importance REAL DEFAULT 0.50,
            confidence REAL DEFAULT 0.70,
            status TEXT DEFAULT 'active',
            fp TEXT UNIQUE,
            hits INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS supermem_person_graph (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair_key TEXT UNIQUE,
            source_user TEXT NOT NULL,
            target_person TEXT NOT NULL,
            relation TEXT DEFAULT '',
            emotion TEXT DEFAULT '',
            maat_field TEXT DEFAULT '',
            strength REAL DEFAULT 0.50,
            evidence_count INTEGER DEFAULT 1,
            confidence REAL DEFAULT 0.50,
            maturity TEXT DEFAULT 'NEW',
            tags TEXT DEFAULT '',
            relation_status TEXT DEFAULT 'inferred',
            last_evidence TEXT DEFAULT '',
            last_seen TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS sm_mem_ts ON supermem_memories(ts);
        CREATE INDEX IF NOT EXISTS sm_mem_layer ON supermem_memories(layer);
        CREATE INDEX IF NOT EXISTS sm_mem_type ON supermem_memories(memory_type);
        CREATE INDEX IF NOT EXISTS sm_mem_author ON supermem_memories(author_user);
        CREATE INDEX IF NOT EXISTS sm_mem_status ON supermem_memories(status);
        CREATE INDEX IF NOT EXISTS sm_pg_source ON supermem_person_graph(source_user);
        CREATE INDEX IF NOT EXISTS sm_pg_target ON supermem_person_graph(target_person);
        CREATE INDEX IF NOT EXISTS sm_pg_maturity ON supermem_person_graph(maturity);
        """
    )
    conn.commit()
    initialize_memory_archive(database)


def _settings(settings: Any) -> dict[str, Any]:
    if isinstance(settings, dict):
        return settings
    try:
        return vars(settings)
    except TypeError:
        return {}


def _norm(text: Any) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _tokens(text: Any) -> list[str]:
    return re.findall(r"[a-zA-Z0-9äöüÄÖÜß_+\-]+", _norm(text))


def _stopwords() -> set[str]:
    return {
        "ich", "du", "der", "die", "das", "ein", "eine", "und", "oder", "aber", "mit",
        "für", "auf", "in", "am", "von", "zu", "ist", "war", "sind", "sein", "habe",
        "hat", "haben", "dass", "ohne", "nicht", "sich", "wie", "was", "wer", "wo",
        "mir", "dir", "mich", "dich", "the", "a", "an", "is", "are", "it", "this",
    }


def _keywords(text: str, limit: int = 10) -> list[str]:
    stop = _stopwords()
    words = [w for w in _tokens(text) if w not in stop and len(w) > 2]
    scored = sorted(set(words), key=lambda word: (-words.count(word), -len(word), word))
    return scored[:limit]


def _fingerprint(text: str) -> str:
    return md5(_norm(text).encode("utf-8")).hexdigest()[:16]


def _compress(text: str, limit: int = 360) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _detect_category(text: str) -> str:
    t = _norm(text)
    scores = {cat: sum(1 for word in words if word in t) for cat, words in CATEGORY_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "allgemein"


def _detect_memory_type(text: str, explicit: str = "") -> str:
    raw = str(explicit or "").strip().lower()
    aliases = {"type": "fact", "technical": "technical", "technik": "technical", "relationship": "relationship", "beziehung": "relationship"}
    if raw:
        return aliases.get(raw, raw)
    t = _norm(text)
    for memory_type, markers in MEMORY_TYPE_MARKERS.items():
        if any(marker in t for marker in markers):
            return memory_type
    return "fact"


def _normalize_field(value: Any, text: str = "") -> str:
    raw = str(value or "").strip().upper()
    if raw in {"H", "B", "S", "V", "R"}:
        return raw
    t = _norm(text)
    if any(word in t for word in ["struktur", "klarheit", "harmonie"]):
        return "H"
    if any(word in t for word in ["balance", "abwägung", "abwaegung", "kritik"]):
        return "B"
    if any(word in t for word in ["kreativ", "idee", "schöpfung", "schoepfung"]):
        return "S"
    if any(word in t for word in ["verbunden", "freund", "familie", "nähe"]):
        return "V"
    if any(word in t for word in ["ehrlich", "respekt", "fakt", "wahrheit"]):
        return "R"
    return ""


def _priority(value: Any = None, text: str = "", always: bool = False) -> float:
    if always:
        return 1.0
    raw = str(value or "").strip().lower()
    if raw in {"critical", "kritisch"}:
        return 0.95
    if raw in {"high", "hoch"}:
        return 0.82
    if raw in {"low", "niedrig"}:
        return 0.35
    if raw in {"normal", "medium", "mittel"}:
        return 0.55
    try:
        return max(0.0, min(float(raw), 1.0))
    except ValueError:
        pass
    memory_type = _detect_memory_type(text)
    return {"identity": 0.88, "preference": 0.76, "decision": 0.76, "project": 0.70, "relationship": 0.68}.get(memory_type, 0.50)


def _importance(text: str) -> float:
    t = _norm(text)
    score = 0.18
    if len(_tokens(text)) >= 8:
        score += 0.12
    if len(_keywords(text)) >= 5:
        score += 0.10
    if any(marker in t for marker in ["merke", "speichere", "wichtig", "entscheidung", "projekt", "paper", "freund", "familie"]):
        score += 0.22
    if _detect_memory_type(text) in {"identity", "preference", "decision", "project", "relationship", "technical"}:
        score += 0.18
    if "?" in str(text):
        score -= 0.12
    return round(max(0.0, min(score, 1.0)), 3)


def _confidence(text: str, memory_type: str, priority: float) -> float:
    base = 0.58 + min(priority, 1.0) * 0.22
    if memory_type in {"identity", "preference", "decision", "project", "relationship"}:
        base += 0.08
    if len(_tokens(text)) < 5:
        base -= 0.10
    return round(max(0.20, min(base, 0.98)), 3)


def _split_csv(value: Any) -> list[str]:
    result = []
    seen = set()
    for part in re.split(r"[,;\n]+", str(value or "")):
        clean = " ".join(part.strip().split())
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            result.append(clean)
    return result


def _current_user(settings: Any) -> str:
    return " ".join(str(_settings(settings).get("supermem_current_user") or "User").split())


def _author_for_role(role: str, settings: Any) -> str:
    return _current_user(settings) if role == "user" else "MAAT KI"


def _same_user(left: Any, right: Any) -> bool:
    return _norm(left).replace("-", " ") == _norm(right).replace("-", " ")


def _author_bonus(row: dict[str, Any], settings: Any) -> float:
    data = _settings(settings)
    if not data.get("supermem_prefer_user_memories", True):
        return 0.0
    author = row.get("author_user") or ""
    current = _current_user(settings)
    if not author or not current:
        return 0.0
    return float(data.get("supermem_user_memory_bonus", 0.12) or 0.12) if _same_user(author, current) else -0.06


def _looks_internal(text: str) -> bool:
    raw = str(text or "")
    return any(marker.lower() in raw.lower() for marker in INTERNAL_MARKERS)


def _looks_image_helper(text: str) -> bool:
    t = _norm(text)
    return any(marker in t for marker in IMAGE_HELPER_MARKERS)


def _looks_command(text: str) -> bool:
    return str(text or "").strip().startswith("/")


def _strip_thinking(text: str) -> str:
    stripped = str(text or "")
    lower = stripped.lower()
    first_close = lower.find("</think>")
    first_open = lower.find("<think>")
    if first_close >= 0 and (first_open < 0 or first_close < first_open):
        stripped = stripped[first_close + len("</think>") :].lstrip()
    stripped = re.sub(r"(?is)<think\b[^>]*>.*?</think>\s*", "", stripped)
    stripped = re.sub(r"(?is)<think\b[^>]*>.*", "", stripped)
    stripped = re.sub(r"(?is)<\|channel>thought[\s\S]*?<channel\|>\s*", "", stripped)
    stripped = re.sub(r"(?is)<\|channel>thought[\s\S]*", "", stripped)
    stripped = re.sub(r"(?is)\[(denken|thinking|gedanken)\].*?\[/\1\]\s*", "", stripped)
    free_span = _free_thinking_prefix_span(stripped)
    if free_span and free_span[0] == 0:
        stripped = stripped[free_span[1] :].lstrip()
    return stripped.strip()


def _manual_save_text(text: str) -> str:
    raw = str(text or "").strip()
    for pattern in MANUAL_SAVE_PATTERNS:
        match = pattern.match(raw)
        if match:
            return (match.group(1) or "").strip()
    return ""


def _add_working(role: str, text: str, settings: Any) -> None:
    if _looks_internal(text) or _looks_image_helper(text):
        return
    WORKING_MEMORY.append(
        {
            "role": role,
            "author_user": _author_for_role(role, settings),
            "content": str(text or "").strip(),
            "ts": time.time(),
            "layer": "working",
        }
    )
    del WORKING_MEMORY[:-MAX_WORKING]


def _store_memory(
    database: Database,
    settings: Any,
    role: str,
    content: str,
    layer: str = "episodic",
    keywords: str = "",
    tags: str = "",
    always: bool = False,
    memory_type: str = "",
    maat_field: str = "",
    priority: Any = None,
) -> int | None:
    clean = " ".join(str(content or "").strip().split())
    if len(clean) < 4 or _looks_internal(clean) or _looks_image_helper(clean):
        return None
    memory_type = _detect_memory_type(clean, memory_type)
    maat_field = _normalize_field(maat_field, clean)
    priority_value = _priority(priority, clean, always)
    importance = _importance(clean)
    confidence = _confidence(clean, memory_type, priority_value)
    keyword_text = ",".join(_split_csv(keywords) or _keywords(clean, 8))
    tag_text = ",".join(_split_csv(tags) or _keywords(clean, 4))
    author = _author_for_role(role, settings)
    now = now_iso()
    fp = _fingerprint(f"{layer}:{clean}")
    ts = time.time()
    cursor = database.connection.execute(
        """
        INSERT INTO supermem_memories
          (layer, ts, role, author_user, content, compressed, keywords, category, memory_type,
           maat_field, tags, priority, importance, confidence, status, fp, hits, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, 1, ?, ?)
        ON CONFLICT(fp) DO UPDATE SET
          hits=hits+1,
          status='active',
          priority=MAX(priority, excluded.priority),
          importance=MAX(importance, excluded.importance),
          confidence=MAX(confidence, excluded.confidence),
          updated_at=excluded.updated_at
        """,
        (
            layer,
            ts,
            role,
            author,
            clean,
            _compress(clean),
            keyword_text,
            _detect_category(clean),
            memory_type,
            maat_field,
            tag_text,
            priority_value,
            importance,
            confidence,
            fp,
            now,
            now,
        ),
    )
    database.connection.commit()
    _update_person_graph_from_text(database, settings, clean, role=role, tags=tag_text, memory_type=memory_type, maat_field=maat_field)
    _prune_memories(database, int(_settings(settings).get("supermem_max_memories", 1000) or 1000))
    return int(cursor.lastrowid) if cursor.lastrowid else None


def _prune_memories(database: Database, max_total: int) -> None:
    max_total = max(100, min(int(max_total or 1000), 20000))
    row = database.connection.execute("SELECT COUNT(*) AS c FROM supermem_memories WHERE status='active'").fetchone()
    count = int(row["c"] if isinstance(row, sqlite3.Row) else row[0])
    if count <= max_total:
        return
    remove = count - max_total
    database.connection.execute(
        """
        UPDATE supermem_memories
        SET status='archived'
        WHERE id IN (
            SELECT id FROM supermem_memories
            WHERE status='active'
            ORDER BY priority ASC, importance ASC, ts ASC
            LIMIT ?
        )
        """,
        (remove,),
    )
    database.connection.commit()


def _recall_working(query: str, settings: Any, limit: int = 3) -> list[dict[str, Any]]:
    query_tokens = set(_keywords(query, 8))
    result = []
    for item in reversed(WORKING_MEMORY):
        if item.get("role") == "user" and not _same_user(item.get("author_user"), _current_user(settings)):
            continue
        tokens = set(_keywords(item.get("content", ""), 12))
        overlap = len(query_tokens & tokens)
        if overlap <= 0:
            continue
        score = overlap / max(len(query_tokens), 1) + _author_bonus(item, settings)
        result.append({**item, "source": "working", "score": round(score, 3), "memory_type": "fact", "category": "working"})
    return sorted(result, key=lambda row: row["score"], reverse=True)[:limit]


def _row_to_item(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["source"] = item.get("layer") or "memory"
    return item


def _score_memory(query: str, row: dict[str, Any], settings: Any) -> float:
    query_tokens = set(_keywords(query, 10))
    haystack = " ".join(str(row.get(key, "") or "") for key in ("content", "keywords", "tags", "category", "memory_type", "maat_field"))
    row_tokens = set(_keywords(haystack, 18))
    if not query_tokens:
        return 0.0
    overlap = len(query_tokens & row_tokens)
    if overlap == 0 and not any(tok in _norm(haystack) for tok in query_tokens):
        return 0.0
    score = overlap / max(len(query_tokens), 1)
    score += float(row.get("importance") or 0.0) * 0.18
    score += float(row.get("priority") or 0.0) * 0.16
    score += float(row.get("confidence") or 0.0) * 0.06
    score += min(int(row.get("hits") or 0), 8) * 0.008
    score += TYPE_BONUS.get(str(row.get("memory_type") or "fact"), 0.0)
    age_days = max((time.time() - float(row.get("ts") or 0)) / 86400.0, 0.0)
    score += max(0.0, 0.08 - age_days * 0.002)
    score += _author_bonus(row, settings)
    return round(score, 3)


def _recall_db(database: Database, query: str, settings: Any, limit: int) -> list[dict[str, Any]]:
    rows = database.connection.execute(
        """
        SELECT *
        FROM supermem_memories
        WHERE status='active'
        ORDER BY ts DESC
        LIMIT 900
        """
    ).fetchall()
    scored = []
    min_score = float(_settings(settings).get("supermem_min_score", 0.15) or 0.15)
    for row in rows:
        item = _row_to_item(row)
        score = _score_memory(query, item, settings)
        if score >= min_score:
            item["score"] = score
            scored.append(item)
    scored.sort(key=lambda item: item["score"], reverse=True)
    top = scored[:limit]
    if top:
        ids = [item["id"] for item in top if item.get("id")]
        placeholders = ",".join("?" for _ in ids)
        database.connection.execute(f"UPDATE supermem_memories SET hits=hits+1 WHERE id IN ({placeholders})", ids)
        database.connection.commit()
    return top


def _person_names(settings: Any) -> list[str]:
    raw = _settings(settings).get("supermem_person_names") or DEFAULT_PERSON_NAMES
    return _split_csv(raw)


def _ambiguous_person_names(settings: Any) -> set[str]:
    raw = _settings(settings).get("supermem_person_ambiguous_names") or ""
    return {_fold_person(item) for item in _split_csv(raw)}


def _remember_person_name(settings: Any, name: str) -> None:
    clean = " ".join(str(name or "").split())
    if not clean:
        return
    data = _settings(settings)
    names = _split_csv(data.get("supermem_person_names") or DEFAULT_PERSON_NAMES)
    if not any(_same_user(clean, item) for item in names):
        names.append(clean)
        if hasattr(settings, "supermem_person_names"):
            setattr(settings, "supermem_person_names", ", ".join(names))
        elif isinstance(settings, dict):
            settings["supermem_person_names"] = ", ".join(names)


def _fold_person(text: str) -> str:
    return _norm(text).translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))


def _extract_person_names(text: str, settings: Any) -> list[str]:
    if not _settings(settings).get("supermem_person_recall", True):
        return []
    folded = _fold_person(text)
    found = []
    for name in _person_names(settings):
        bits = [re.escape(part) for part in re.split(r"[\s\-]+", _fold_person(name)) if part]
        if not bits:
            continue
        pattern = r"\b" + r"[\s\-]+".join(bits) + r"\b"
        if re.search(pattern, folded) and name not in found:
            found.append(name)
    return found


def _recall_person_memories(database: Database, query: str, settings: Any, limit: int) -> list[dict[str, Any]]:
    names = _extract_person_names(query, settings)
    if not names:
        return []
    clauses = []
    params: list[Any] = []
    for name in names:
        clauses.append("(LOWER(content) LIKE ? OR LOWER(keywords) LIKE ? OR LOWER(tags) LIKE ?)")
        folded = f"%{name.lower()}%"
        params.extend([folded, folded, folded])
    rows = database.connection.execute(
        f"""
        SELECT *
        FROM supermem_memories
        WHERE status='active' AND ({' OR '.join(clauses)})
        ORDER BY priority DESC, importance DESC, ts DESC
        LIMIT ?
        """,
        [*params, max(limit * 3, limit)],
    ).fetchall()
    out = []
    for row in rows:
        item = _row_to_item(row)
        item["source"] = "person"
        item["score"] = round(0.85 + float(item.get("priority") or 0) * 0.2 + _author_bonus(item, settings), 3)
        out.append(item)
    return out[:limit]


def _relation_terms(query: str) -> list[str]:
    folded = _fold_person(query)
    terms = {
        "bruder": ["bruder", "brueder", "brüder"],
        "schwester": ["schwester"],
        "mutter": ["mutter", "mama"],
        "vater": ["vater", "papa"],
        "grossmutter": ["oma", "omas", "grossmutter", "großmutter"],
        "grossvater": ["opa", "opas", "grossvater", "großvater"],
        "freund": ["freund", "freunde"],
        "freundin": ["freundin"],
        "patentante": ["patentante"],
        "tante": ["tante"],
        "onkel": ["onkel"],
        "partner": ["partner"],
        "partnerin": ["partnerin"],
    }
    found = []
    if not re.search(r"\bwer\s+(?:ist|sind|war|waren)\s+(?:mein|meine|meiner|meinen)\b|\bmein(?:e|er|en)?\s+\w+", folded):
        return []
    for canonical, variants in terms.items():
        if any(re.search(rf"\b{re.escape(_fold_person(variant))}\b", folded) for variant in variants):
            found.append(canonical)
    return found


def _person_graph_pair(source: str, target: str) -> str:
    return f"{_fold_person(source)}::{_fold_person(target)}"


def _graph_maturity(evidence_count: int, strength: float, confidence: float, status: str) -> str:
    if status == "confirmed" and evidence_count >= 12 and strength >= 0.85 and confidence >= 0.82:
        return "CORE"
    if evidence_count >= 6 and confidence >= 0.70:
        return "ESTABLISHED"
    if evidence_count >= 3:
        return "PROMISING"
    return "NEW"


def _detect_relation(text: str, name: str) -> tuple[str, str, float]:
    folded = _fold_person(text)
    target = _fold_person(name)
    patterns = [
        (r"(?:mein|meine|meiner)\s+freund\s+" + re.escape(target), "Freund", "confirmed", 0.86),
        (r"(?:mein|meine|meiner)\s+freundin\s+" + re.escape(target), "Freundin", "confirmed", 0.86),
        (r"(?:mein|meine|meiner)\s+bruder\s+(?:heisst|heißt|ist)?\s*" + re.escape(target), "Bruder", "confirmed", 0.92),
        (re.escape(target) + r"\s+ist\s+(?:mein|meine|meiner)\s+bruder", "Bruder", "confirmed", 0.92),
        (r"(?:mein|meine|meiner)\s+schwester\s+(?:heisst|heißt|ist)?\s*" + re.escape(target), "Schwester", "confirmed", 0.92),
        (re.escape(target) + r"\s+ist\s+(?:mein|meine|meiner)\s+schwester", "Schwester", "confirmed", 0.92),
        (re.escape(target) + r"\s+ist\s+(?:mein|meine|meiner)\s+freund", "Freund", "confirmed", 0.84),
        (re.escape(target) + r"\s+ist\s+(?:mein|meine|meiner)\s+freundin", "Freundin", "confirmed", 0.84),
        (re.escape(target) + r".{0,32}\s+freund\s+des\s+users", "Freund", "confirmed", 0.80),
        (re.escape(target) + r".{0,32}\s+freund\s+des\s+nutzers", "Freund", "confirmed", 0.80),
        (re.escape(target) + r"\s+ist\s+(?:mein|meine|meiner)\s+patentante", "Patentante", "confirmed", 0.90),
        (re.escape(target) + r"\s+ist\s+(?:mein|meine|meiner)\s+oma", "Großmutter", "confirmed", 0.92),
        (re.escape(target) + r"\s+ist\s+(?:mein|meine|meiner)\s+opa", "Großvater", "confirmed", 0.92),
    ]
    for pattern, relation, status, confidence in patterns:
        if re.search(pattern, folded):
            return relation, status, confidence
    if name:
        return "erwähnte Person", "inferred", 0.42
    return "", "inferred", 0.30


def _detect_person_emotion(text: str) -> str:
    folded = _fold_person(text)
    if any(word in folded for word in ["vermisse", "trauer", "verstorben", "denke oft"]):
        return "warme Verbundenheit / Trauer"
    if any(word in folded for word in ["mag", "gern", "freue", "spaß", "spass"]):
        return "positive Verbundenheit"
    if any(word in folded for word in ["streit", "wut", "schwierig", "konflikt"]):
        return "angespannte Beziehung"
    return "neutral"


def _update_person_graph_from_text(
    database: Database,
    settings: Any,
    text: str,
    role: str = "user",
    tags: str = "",
    memory_type: str = "",
    maat_field: str = "",
) -> int:
    if not _settings(settings).get("supermem_person_graph", True):
        return 0
    source = _current_user(settings) if role == "user" else _current_user(settings)
    count = 0
    ambiguous = _ambiguous_person_names(settings)
    for name in _extract_person_names(text, settings):
        if _same_user(name, source):
            continue
        relation, status, relation_conf = _detect_relation(text, name)
        if _fold_person(name) in ambiguous and status != "confirmed":
            continue
        if status != "confirmed" and memory_type not in {"relationship", "identity"}:
            continue
        emotion = _detect_person_emotion(text)
        strength = 0.60 if status == "confirmed" else 0.42
        if emotion != "neutral":
            strength += 0.12
        pair_key = _person_graph_pair(source, name)
        now = now_iso()
        existing = database.connection.execute(
            "SELECT * FROM supermem_person_graph WHERE pair_key = ?",
            (pair_key,),
        ).fetchone()
        if existing:
            evidence_count = int(existing["evidence_count"] or 0) + 1
            new_strength = min(1.0, max(float(existing["strength"] or 0.5), strength) + 0.02)
            new_conf = min(1.0, max(float(existing["confidence"] or 0.5), relation_conf) + 0.01)
            final_status = "confirmed" if status == "confirmed" or existing["relation_status"] == "confirmed" else "inferred"
            final_relation = relation if status == "confirmed" else (existing["relation"] or relation)
            maturity = _graph_maturity(evidence_count, new_strength, new_conf, final_status)
            database.connection.execute(
                """
                UPDATE supermem_person_graph
                SET relation=?, emotion=?, maat_field=?, strength=?, evidence_count=?,
                    confidence=?, maturity=?, tags=?, relation_status=?, last_evidence=?,
                    last_seen=?, updated_at=?
                WHERE pair_key=?
                """,
                (
                    final_relation,
                    emotion if emotion != "neutral" else existing["emotion"] or emotion,
                    maat_field or existing["maat_field"] or "",
                    new_strength,
                    evidence_count,
                    new_conf,
                    maturity,
                    tags or existing["tags"] or "",
                    final_status,
                    _compress(text, 180),
                    now,
                    now,
                    pair_key,
                ),
            )
        else:
            maturity = _graph_maturity(1, strength, relation_conf, status)
            database.connection.execute(
                """
                INSERT INTO supermem_person_graph
                  (pair_key, source_user, target_person, relation, emotion, maat_field,
                   strength, evidence_count, confidence, maturity, tags, relation_status,
                   last_evidence, last_seen, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pair_key,
                    source,
                    name,
                    relation,
                    emotion,
                    maat_field or "",
                    strength,
                    relation_conf,
                    maturity,
                    tags,
                    status,
                    _compress(text, 180),
                    now,
                    now,
                    now,
                ),
            )
        count += 1
    if count:
        database.connection.commit()
        if _settings(settings).get("supermem_debug", False):
            print(f"[MAAT Web Core][person_graph] auto-update source={source} count={count} evidence='{_compress(text, 100)}'")
    return count


def _recall_person_graph(database: Database, query: str, settings: Any, limit: int) -> list[dict[str, Any]]:
    if not _settings(settings).get("supermem_person_graph", True):
        return []
    names = _extract_person_names(query, settings)
    terms = _relation_terms(query)
    params: list[Any] = [_current_user(settings)]
    where = ["source_user = ?"]
    if names:
        name_clauses = []
        for name in names:
            name_clauses.append("LOWER(target_person) LIKE ?")
            params.append(f"%{name.lower()}%")
        where.append("(" + " OR ".join(name_clauses) + ")")
    if terms:
        term_clauses = []
        for term in terms:
            term_clauses.append("LOWER(relation) LIKE ?")
            params.append(f"%{term.lower()}%")
        where.append("(" + " OR ".join(term_clauses) + ")")
    if not names and not terms:
        return []
    rows = database.connection.execute(
        f"""
        SELECT *
        FROM supermem_person_graph
        WHERE {' AND '.join(where)}
        ORDER BY relation_status DESC, confidence DESC, evidence_count DESC, updated_at DESC
        LIMIT ?
        """,
        [*params, max(1, limit)],
    ).fetchall()
    out = []
    for row in rows:
        text = (
            f"Person Graph: {_current_user(settings)} -> {row['target_person']}: "
            f"relation={row['relation'] or 'erwähnte Person'}, emotion={row['emotion'] or 'neutral'}, "
            f"maturity={row['maturity']}, status={row['relation_status']}, "
            f"confidence={float(row['confidence'] or 0):.2f}; details={row['last_evidence'] or ''}"
        )
        out.append(
            {
                "id": row["id"],
                "source": "person_graph",
                "layer": "person_graph",
                "content": text,
                "category": "beziehung",
                "memory_type": "relationship",
                "maat_field": row["maat_field"] or "V",
                "tags": row["tags"] or "",
                "author_user": row["source_user"],
                "score": round(1.1 + float(row["confidence"] or 0) * 0.3, 3),
                "ts": time.time(),
            }
        )
    return out


def _person_graph_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    get = row.get if isinstance(row, dict) else row.__getitem__
    return {
        "id": int(get("id") or 0),
        "pair_key": str(get("pair_key") or ""),
        "source_user": str(get("source_user") or ""),
        "target_person": str(get("target_person") or ""),
        "relation": str(get("relation") or ""),
        "emotion": str(get("emotion") or ""),
        "maat_field": str(get("maat_field") or ""),
        "strength": float(get("strength") or 0.0),
        "evidence_count": int(get("evidence_count") or 0),
        "confidence": float(get("confidence") or 0.0),
        "maturity": str(get("maturity") or "NEW"),
        "tags": str(get("tags") or ""),
        "relation_status": str(get("relation_status") or "inferred"),
        "last_evidence": str(get("last_evidence") or ""),
        "last_seen": str(get("last_seen") or ""),
        "created_at": str(get("created_at") or ""),
        "updated_at": str(get("updated_at") or ""),
    }


def _person_graph_summary(row: dict[str, Any]) -> str:
    relation = row.get("relation") or "erwähnte Person"
    emotion = row.get("emotion") or "neutral"
    return (
        f"{row.get('source_user')} -> {row.get('target_person')} | {relation} | {emotion} | "
        f"{row.get('relation_status')} | {row.get('maturity')} | "
        f"conf={float(row.get('confidence') or 0):.2f} evidence={int(row.get('evidence_count') or 0)}"
    )


def person_graph_state(database: Database, settings: Any, source_user: str = "", limit: int = 120) -> dict[str, Any]:
    current = " ".join(str(source_user or _current_user(settings)).split()) or "User"
    max_rows = max(10, min(int(limit or 120), 500))
    rows = database.connection.execute(
        """
        SELECT *
        FROM supermem_person_graph
        WHERE source_user = ?
        ORDER BY relation_status DESC, confidence DESC, evidence_count DESC, updated_at DESC
        LIMIT ?
        """,
        (current, max_rows),
    ).fetchall()
    entries = [_person_graph_row(row) for row in rows]
    for entry in entries:
        entry["summary"] = _person_graph_summary(entry)
    return {
        "ok": True,
        "source_user": current,
        "count": len(entries),
        "entries": entries,
        "person_names": _person_names(settings),
        "ambiguous_names": sorted(_ambiguous_person_names(settings)),
    }


def person_graph_upsert(database: Database, settings: Any, payload: dict[str, Any]) -> dict[str, Any]:
    source = " ".join(str(payload.get("source_user") or _current_user(settings)).split()) or "User"
    target = " ".join(str(payload.get("target_person") or "").split())
    if not target:
        raise ValueError("target_person fehlt.")

    relation = " ".join(str(payload.get("relation") or "erwähnte Person").split())
    emotion = " ".join(str(payload.get("emotion") or "neutral").split())
    maat_field = str(payload.get("maat_field") or "V").strip().upper()[:1]
    if maat_field not in {"H", "B", "S", "V", "R"}:
        maat_field = "V"
    tags = str(payload.get("tags") or "").strip()
    relation_status = str(payload.get("relation_status") or "confirmed").strip().lower()
    if relation_status not in {"confirmed", "inferred", "mentioned"}:
        relation_status = "confirmed"
    try:
        strength = max(0.0, min(1.0, float(payload.get("strength", 1.0))))
    except (TypeError, ValueError):
        strength = 1.0
    try:
        confidence = max(0.0, min(1.0, float(payload.get("confidence", 1.0))))
    except (TypeError, ValueError):
        confidence = 1.0
    try:
        evidence_count = max(1, min(10000, int(payload.get("evidence_count", 1))))
    except (TypeError, ValueError):
        evidence_count = 1

    maturity = str(payload.get("maturity") or "").strip().upper()
    if maturity not in {"NEW", "PROMISING", "ESTABLISHED", "CORE"}:
        maturity = _graph_maturity(evidence_count, strength, confidence, relation_status)

    now = now_iso()
    evidence = _compress(str(payload.get("last_evidence") or ""), 600)
    pair_key = _person_graph_pair(source, target)
    graph_id = str(payload.get("id") or "").strip()
    existing = None
    if graph_id:
        existing = database.connection.execute("SELECT * FROM supermem_person_graph WHERE id = ?", (graph_id,)).fetchone()
    if not existing:
        existing = database.connection.execute("SELECT * FROM supermem_person_graph WHERE pair_key = ?", (pair_key,)).fetchone()

    if existing:
        database.connection.execute(
            """
            UPDATE supermem_person_graph
            SET pair_key=?, source_user=?, target_person=?, relation=?, emotion=?, maat_field=?,
                strength=?, evidence_count=?, confidence=?, maturity=?, tags=?, relation_status=?,
                last_evidence=?, last_seen=?, updated_at=?
            WHERE id=?
            """,
            (
                pair_key,
                source,
                target,
                relation,
                emotion,
                maat_field,
                strength,
                evidence_count,
                confidence,
                maturity,
                tags,
                relation_status,
                evidence,
                now,
                now,
                int(existing["id"]),
            ),
        )
        graph_id = str(existing["id"])
    else:
        cursor = database.connection.execute(
            """
            INSERT INTO supermem_person_graph
              (pair_key, source_user, target_person, relation, emotion, maat_field,
               strength, evidence_count, confidence, maturity, tags, relation_status,
               last_evidence, last_seen, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pair_key,
                source,
                target,
                relation,
                emotion,
                maat_field,
                strength,
                evidence_count,
                confidence,
                maturity,
                tags,
                relation_status,
                evidence,
                now,
                now,
                now,
            ),
        )
        graph_id = str(cursor.lastrowid)
    database.connection.commit()
    _remember_person_name(settings, target)
    if _settings(settings).get("supermem_debug", False):
        print(
            "[MAAT Web Core][person_graph] UI-UPDATE "
            f"source_user={source} target_person={target} relation={relation} "
            f"emotion={emotion} status={relation_status} maturity={maturity} "
            f"strength={strength:.2f} confidence={confidence:.2f} evidence_count={evidence_count} "
            f"evidence='{_compress(evidence, 120)}'"
        )
    state = person_graph_state(database, settings, source)
    state["selected_id"] = int(graph_id or 0)
    return state


def person_graph_delete(database: Database, settings: Any, payload: dict[str, Any]) -> dict[str, Any]:
    source = " ".join(str(payload.get("source_user") or _current_user(settings)).split()) or "User"
    graph_id = str(payload.get("id") or "").strip()
    if not graph_id:
        raise ValueError("id fehlt.")
    row = database.connection.execute("SELECT * FROM supermem_person_graph WHERE id = ?", (graph_id,)).fetchone()
    database.connection.execute("DELETE FROM supermem_person_graph WHERE id = ?", (graph_id,))
    database.connection.commit()
    if row and _settings(settings).get("supermem_debug", False):
        print(
            "[MAAT Web Core][person_graph] UI-DELETE "
            f"source_user={row['source_user']} target_person={row['target_person']} id={graph_id}"
        )
    return person_graph_state(database, settings, source)


def _time_window(query: str) -> dict[str, Any] | None:
    folded = _fold_person(query)
    now = datetime.now()
    today = datetime(year=now.year, month=now.month, day=now.day)

    def day_window(days_ago: int, label: str) -> dict[str, Any]:
        start = today - timedelta(days=days_ago)
        end = start + timedelta(days=1)
        return {"start": start.timestamp(), "end": end.timestamp(), "label": label, "kind": "day"}

    if "vorgestern" in folded:
        return day_window(2, "vorgestern")
    if "gestern" in folded:
        return day_window(1, "gestern")

    match = re.search(r"\bvor\s+(\d{1,4})\s+(tag|tagen|woche|wochen|monat|monaten|jahr|jahren)\b", folded)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("tag"):
            return day_window(value, f"vor {value} Tagen")
        if unit.startswith("woche"):
            days = value * 7
            center = today - timedelta(days=days)
            return {"start": (center - timedelta(days=3)).timestamp(), "end": (center + timedelta(days=4)).timestamp(), "label": f"vor {value} Wochen", "kind": "around"}
        if unit.startswith("monat"):
            days = value * 30
            center = today - timedelta(days=days)
            return {"start": (center - timedelta(days=5)).timestamp(), "end": (center + timedelta(days=6)).timestamp(), "label": f"vor {value} Monaten", "kind": "around"}
        if unit.startswith("jahr"):
            days = value * 365
            center = today - timedelta(days=days)
            return {"start": (center - timedelta(days=14)).timestamp(), "end": (center + timedelta(days=15)).timestamp(), "label": f"vor {value} Jahren", "kind": "around"}

    date_match = re.search(r"\b(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](20\d{2}|19\d{2}))?\b", folded)
    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year = int(date_match.group(3) or now.year)
        try:
            start = datetime(year=year, month=month, day=day)
            return {"start": start.timestamp(), "end": (start + timedelta(days=1)).timestamp(), "label": start.strftime("%d.%m.%Y"), "kind": "day"}
        except ValueError:
            return None

    month_names = {
        "januar": 1, "februar": 2, "maerz": 3, "märz": 3, "april": 4, "mai": 5, "juni": 6,
        "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12,
    }
    for name, month in month_names.items():
        match = re.search(rf"\b(\d{{1,2}})\.?\s+{name}(?:\s+(20\d{{2}}|19\d{{2}}))?\b", folded)
        if match:
            year = int(match.group(2) or now.year)
            start = datetime(year=year, month=month, day=int(match.group(1)))
            return {"start": start.timestamp(), "end": (start + timedelta(days=1)).timestamp(), "label": start.strftime("%d.%m.%Y"), "kind": "day"}
    return None


def _recall_time(database: Database, query: str, settings: Any, limit: int) -> list[dict[str, Any]]:
    window = _time_window(query)
    if not window:
        return []
    rows = database.connection.execute(
        """
        SELECT *
        FROM supermem_memories
        WHERE status='active' AND ts >= ? AND ts < ?
        ORDER BY priority DESC, importance DESC, ts DESC
        LIMIT ?
        """,
        (window["start"], window["end"], max(limit, 10)),
    ).fetchall()
    items = []
    for row in rows:
        item = _row_to_item(row)
        item["source"] = "time"
        item["time_window"] = window["label"]
        item["score"] = round(0.95 + float(item.get("priority") or 0) * 0.2 + _author_bonus(item, settings), 3)
        items.append(item)
    items.extend(recall_archived_sources_for_window(database, window, settings, limit))
    if not items and window.get("kind") == "day":
        start = float(window["start"])
        fallback = database.connection.execute(
            """
            SELECT *
            FROM supermem_memories
            WHERE status='active' AND ts >= ? AND ts < ?
            ORDER BY ABS(ts - ?) ASC, priority DESC
            LIMIT ?
            """,
            (start - 86400 * 3, start + 86400 * 4, start, limit),
        ).fetchall()
        for row in fallback:
            item = _row_to_item(row)
            item["source"] = "time"
            item["time_exact_miss"] = window["label"]
            item["time_window"] = f"{window['label']} ±3 Tage"
            item["score"] = round(0.72 + float(item.get("priority") or 0) * 0.2 + _author_bonus(item, settings), 3)
            items.append(item)
    if not items or window.get("kind") != "day":
        archive_items = recall_archive_for_window(database, window, settings, limit)
        if archive_items:
            if window.get("kind") == "day" and not items:
                for item in archive_items:
                    item["time_exact_miss"] = window["label"]
            items.extend(archive_items)
    return items[:limit]


def recall_memories(database: Database, settings: Any, query: str) -> list[dict[str, Any]]:
    data = _settings(settings)
    if not data.get("supermem_enabled", True) or not data.get("supermem_autorecall", True):
        return []
    top_k = max(1, min(int(data.get("supermem_top_k", 5) or 5), 20))
    graph_top = max(0, min(int(data.get("supermem_person_graph_top_k", 2) or 2), 10))
    person_top = max(0, min(int(data.get("supermem_person_top_k", 4) or 4), 10))
    candidates = []
    candidates.extend(_recall_time(database, query, settings, top_k))
    candidates.extend(_recall_person_graph(database, query, settings, graph_top))
    candidates.extend(_recall_person_memories(database, query, settings, person_top))
    candidates.extend(_recall_working(query, settings, 3))
    candidates.extend(_recall_db(database, query, settings, top_k * 3))
    seen = set()
    out = []
    for item in sorted(candidates, key=lambda row: float(row.get("score") or 0), reverse=True):
        content = item.get("content") or ""
        fp = _fingerprint(content)
        if fp in seen:
            continue
        seen.add(fp)
        out.append(item)
        if len(out) >= top_k:
            break
    return out


def _relative_time(ts: Any) -> str:
    try:
        seconds = max(0, int(time.time() - float(ts)))
    except (TypeError, ValueError):
        return ""
    days = seconds // 86400
    if days == 0:
        hours = seconds // 3600
        if hours <= 0:
            return "gerade eben"
        return f"vor {hours} Stunde{'n' if hours != 1 else ''}"
    if days == 1:
        return "gestern"
    if days == 2:
        return "vorgestern"
    if days < 7:
        return f"vor {days} Tagen"
    weeks, rest = divmod(days, 7)
    if days < 31:
        return f"vor {weeks} Woche{'n' if weeks != 1 else ''}" + (f" und {rest} Tag{'en' if rest != 1 else ''}" if rest else "")
    months = days // 30
    if days < 365:
        return f"vor {months} Monat{'en' if months != 1 else ''}"
    years = days // 365
    return f"vor {years} Jahr{'en' if years != 1 else ''}"


def format_memory_block(memories: list[dict[str, Any]], settings: Any) -> str:
    current = _current_user(settings)
    lines = [
        "[MAAT_MEMORY]",
        "Nutze diese Erinnerungen nur still als Kontext. Nicht zitieren, wenn es nicht hilft.",
        f"Aktueller menschlicher Schreiber: {current}",
        "Erwähnte Namen im Usertext sind nicht automatisch der Autor.",
    ]
    if memories:
        lines.append("Relevante Erinnerungen:")
        for index, item in enumerate(memories, 1):
            source = item.get("source") or item.get("layer") or "memory"
            rel = _relative_time(item.get("ts"))
            author = item.get("author_user") or ""
            meta = "/".join(part for part in [source, item.get("category"), item.get("memory_type"), item.get("maat_field")] if part)
            author_part = f" author={author}" if author else ""
            time_part = f" time={rel}" if rel else ""
            miss_part = f" exact_miss={item.get('time_exact_miss')}" if item.get("time_exact_miss") else ""
            lines.append(f"{index}. [{meta}{author_part}{time_part}{miss_part}] {_compress(item.get('content', ''), 280)}")
    else:
        lines.append("Keine passenden Erinnerungen gefunden.")
    lines.append("[/MAAT_MEMORY]")
    return "\n".join(lines)


def save_reminder_block(settings: Any) -> str:
    if not _settings(settings).get("supermem_allow_model_saves", True):
        return ""
    current = _current_user(settings)
    return (
        "\n\n[MAAT_MEMORY_SAVE_REMINDER]\n"
        "Stille interne Anleitung fuer MAAT Super Memory. Nicht zitieren, nicht erklaeren, nicht sichtbar als Regel ausgeben.\n"
        f"Aktueller menschlicher Schreiber: {current}. Speichere neue User-Fakten im Inhalt mit diesem Namen, wenn relevant.\n"
        "Wenn eine wirklich speicherwuerdige neue Information entsteht, schreibe ganz am Ende hoechstens ein save:(...).\n"
        "Format: save: (memory=<klarer Inhalt>, keywords=<2-4 keywords>, tags=<tags>, always=false, "
        "type=<identity|preference|project|decision|fact|temporary|relationship|technical>, field=<H|B|S|V|R>, priority=<low|normal|high|critical>)\n"
        "Speichern JA: Identitaet, Vorlieben, stabile Beziehungen, Projektentscheidungen, wichtige technische Fixes, Termine/kurzfristige Plaene, explizites 'merke dir'.\n"
        "Speichern NEIN: reine Begruessung, Danke, Wiederholung, interne Denkspur, Prompt/MAAT-Tags, Bildgenerator-Hilfstext, Code der nur gerade ausgefuehrt wird, unsichere Vermutungen.\n"
        "Nutze always=true nur fuer dauerhafte Identitaet/Core-Fakten. Nutze temporary fuer Termine und heutige Plaene. Nutze relationship fuer Personen/Familie/Freunde.\n"
        "Memory-Inhalt kurz, eindeutig und ohne Meta-Satz formulieren. Keine erfundenen Details. Erwaehnte Namen sind nicht automatisch der Autor.\n"
        "Gutes Beispiel: save: (memory=User trifft heute um 13 Uhr eine Kontaktperson, keywords=treffen,13-uhr, tags=beziehung,termin, always=false, type=temporary, field=V, priority=normal)\n"
        "Bei Code-/Datei-/Toolaufgaben niemals nur save ausgeben; zuerst die vollständige Antwort.\n"
        "[/MAAT_MEMORY_SAVE_REMINDER]"
    )


def build_memory_prompt(database: Database, settings: Any, user_input: str) -> tuple[str, dict[str, Any]]:
    data = _settings(settings)
    info = {"enabled": bool(data.get("supermem_enabled", True)), "memories": [], "current_user": _current_user(settings)}
    if not info["enabled"]:
        return "", info
    memories = recall_memories(database, settings, user_input)
    info["memories"] = memories
    prompt = format_memory_block(memories, settings) + save_reminder_block(settings)
    return "\n\n" + prompt, info


def _autostore_decision(role: str, text: str, settings: Any) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {"store": False, "reason": "empty", "score": 0.0}
    if _looks_internal(raw):
        return {"store": False, "reason": "internal", "score": 0.0}
    if _looks_image_helper(raw):
        return {"store": False, "reason": "image-helper", "score": 0.0}
    if _looks_command(raw):
        return {"store": False, "reason": "command", "score": 0.0}
    if _manual_save_text(raw):
        return {"store": False, "reason": "manual-save", "score": 0.0}
    if len(_tokens(raw)) < 5:
        return {"store": False, "reason": "too-short", "score": 0.0}
    max_chars = int(_settings(settings).get("supermem_autostore_max_chars", 1200) or 1200)
    if len(raw) > max_chars:
        raw = _compress(raw, max_chars)
    if role == "assistant" and not _settings(settings).get("supermem_autostore_assistant", False):
        return {"store": False, "reason": "assistant-autostore-off", "score": 0.0}
    score = _importance(raw)
    memory_type = _detect_memory_type(raw)
    score += TYPE_BONUS.get(memory_type, 0.0)
    if role == "assistant":
        score -= 0.16
    threshold = float(
        _settings(settings).get(
            "supermem_autostore_assistant_min" if role == "assistant" else "supermem_autostore_user_min",
            0.62 if role == "assistant" else 0.38,
        )
        or 0.38
    )
    return {
        "store": score >= threshold,
        "reason": "importance" if score >= threshold else "below-threshold",
        "score": round(max(0.0, min(score, 1.0)), 3),
        "text": raw,
        "memory_type": memory_type,
    }


def _scan_wrapped_save(text: str, start: int, opener: str, closer: str) -> tuple[int, str]:
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth <= 0:
                return index + 1, text[start + 1 : index]
        index += 1
    line_end = text.find("\n", start)
    if line_end < 0:
        line_end = len(text)
    return line_end, text[start + 1 : line_end].rstrip(") }")


def _iter_save_spans(text: str) -> list[tuple[int, int, str]]:
    spans = []
    pos = 0
    while True:
        match = SAVE_START_RE.search(text, pos)
        if not match:
            break
        value_start = match.end()
        while value_start < len(text) and text[value_start].isspace():
            value_start += 1
        if value_start >= len(text):
            spans.append((match.start(), value_start, ""))
            break
        first = text[value_start]
        if first == "(":
            end, raw = _scan_wrapped_save(text, value_start, "(", ")")
        elif first == "{":
            end, raw_inner = _scan_wrapped_save(text, value_start, "{", "}")
            raw = "{" + raw_inner + "}"
        else:
            end = text.find("\n", value_start)
            if end < 0:
                end = len(text)
            raw = text[value_start:end]
        spans.append((match.start(), end, raw.strip()))
        pos = max(end, match.end() + 1)
    return spans


def _protected_spans(text: str) -> list[tuple[int, int]]:
    patterns = [
        r"(?is)<think\b[^>]*>.*?(?:</think>|$)",
        r"(?is)<\|channel>thought[\s\S]*?(?:<channel\|>|$)",
        r"(?is)<details\b[^>]*(?:thinking|reasoning|denken|maat-memory-save-box)[^>]*>.*?</details>",
        r"(?is)\[(denken|thinking|gedanken)\].*?(?:\[/\1\]|$)",
        r"(?is)\[MAAT_[A-Z_]+[^\]]*\].*?\[/MAAT_[A-Z_]+\]",
    ]
    spans = []
    for pattern in patterns:
        spans.extend((match.start(), match.end()) for match in re.finditer(pattern, text or ""))
    free_span = _free_thinking_prefix_span(text or "")
    if free_span:
        spans.append(free_span)
    return spans


def _in_spans(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in spans)


def _free_thinking_prefix_span(text: str) -> tuple[int, int] | None:
    raw = str(text or "")
    if not raw:
        return None
    starts_like_thinking = bool(FREE_THINKING_START_RE.match(raw))
    if not starts_like_thinking and not INTERNAL_THINKING_HINT_RE.search(raw[:5000]):
        return None

    label = FINAL_ANSWER_LABEL_RE.search(raw)
    if label and label.end() < len(raw):
        return 0, label.end()

    for match in FINAL_ANSWER_START_RE.finditer(raw):
        answer_start = match.start("answer")
        if answer_start >= 24 and (starts_like_thinking or INTERNAL_THINKING_HINT_RE.search(raw[:answer_start])):
            return 0, answer_start

    # If it looks like pure unfinished thinking, protect the whole answer from
    # model-save extraction. Visible final-answer saves are still handled when a
    # final-answer boundary is found.
    if starts_like_thinking:
        return 0, len(raw)
    return None


def _parse_save_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "ja", "on"}


def _clean_save_value(value: str) -> str:
    value = str(value or "").strip().strip(",")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def _parse_save(raw: str) -> dict[str, Any] | None:
    raw = str(raw or "").strip()
    if not raw:
        return None
    if raw.startswith("{"):
        try:
            obj = json.loads(raw)
            memory = str(obj.get("memory", "")).strip()
            if not memory:
                return None
            return {
                "memory": memory,
                "keywords": str(obj.get("keywords", "")).strip(),
                "tags": str(obj.get("tags", "")).strip(),
                "always": _parse_save_bool(obj.get("always", False)),
                "memory_type": _detect_memory_type(memory, obj.get("memory_type") or obj.get("type") or ""),
                "maat_field": _normalize_field(obj.get("maat_field") or obj.get("field") or "", memory),
                "priority": _priority(obj.get("priority"), memory, _parse_save_bool(obj.get("always", False))),
            }
        except Exception:
            pass
    fields: dict[str, str] = {}
    for match in SAVE_KV_RE.finditer(raw):
        fields[match.group(1).lower()] = _clean_save_value(match.group(2))
    if fields:
        memory = fields.get("memory", "").strip()
        if not memory:
            return None
        always = _parse_save_bool(fields.get("always", False))
        return {
            "memory": memory,
            "keywords": fields.get("keywords", ""),
            "tags": fields.get("tags", ""),
            "always": always,
            "memory_type": _detect_memory_type(memory, fields.get("memory_type") or fields.get("type") or ""),
            "maat_field": _normalize_field(fields.get("maat_field") or fields.get("field") or "", memory),
            "priority": _priority(fields.get("priority"), memory, always),
        }
    return {
        "memory": raw,
        "keywords": "",
        "tags": "",
        "always": False,
        "memory_type": _detect_memory_type(raw),
        "maat_field": _normalize_field("", raw),
        "priority": _priority(None, raw),
    }


def extract_model_saves(text: str) -> tuple[str, list[dict[str, Any]]]:
    raw = str(text or "")
    protected = _protected_spans(raw)
    spans = []
    saves = []
    for start, end, body in _iter_save_spans(raw):
        if _in_spans(start, protected):
            continue
        parsed = _parse_save(body)
        if not parsed or not parsed.get("memory"):
            continue
        spans.append((start, end))
        saves.append(parsed)
    if not spans:
        return raw, []
    cleaned = []
    pos = 0
    for start, end in spans:
        cleaned.append(raw[pos:start])
        pos = end
    cleaned.append(raw[pos:])
    return re.sub(r"\n{3,}", "\n\n", "".join(cleaned)).strip(), saves


def _save_directive(save: dict[str, Any]) -> str:
    priority = save.get("priority", 0.5)
    if isinstance(priority, float):
        priority_text = f"{priority:.2f}"
    else:
        priority_text = str(priority)
    return (
        "save: ("
        f"memory={save.get('memory', '')}, "
        f"keywords={save.get('keywords', '')}, "
        f"tags={save.get('tags', '')}, "
        f"always={str(bool(save.get('always', False))).lower()}, "
        f"type={save.get('memory_type', 'fact')}, "
        f"field={save.get('maat_field', '')}, "
        f"priority={priority_text}"
        ")"
    )


def _save_box(saves: list[dict[str, Any]]) -> str:
    parts = []
    for index, save in enumerate(saves, 1):
        title = "Erinnerung angelegt" if len(saves) == 1 else f"Erinnerung {index}/{len(saves)} angelegt"
        escaped = html.escape(_save_directive(save), quote=False)
        parts.append(
            "\n<details class=\"maat-memory-save-box\">\n"
            f"<summary>🧠 {title} — mehr anzeigen</summary>\n"
            f"<pre><code>{escaped}</code></pre>\n"
            "</details>\n"
        )
    return "\n".join(parts)


def process_turn_memory(database: Database, settings: Any, user_input: str, assistant_output: str) -> tuple[str, dict[str, Any]]:
    data = _settings(settings)
    info = {"stored_saves": [], "autostore": [], "debug": []}
    if not data.get("supermem_enabled", True):
        return assistant_output, info

    _add_working("user", user_input, settings)
    manual = _manual_save_text(user_input)
    if manual:
        _store_memory(database, settings, "user", manual, layer="episodic")
        _store_memory(database, settings, "user", manual, layer="semantic")
        info["autostore"].append({"role": "user", "reason": "manual-save", "text": manual})

    visible_output, saves = extract_model_saves(assistant_output)
    stored_saves = []
    if saves and data.get("supermem_allow_model_saves", True):
        for save in saves:
            _store_memory(
                database,
                settings,
                "assistant",
                save["memory"],
                layer="episodic",
                keywords=save.get("keywords", ""),
                tags=save.get("tags", ""),
                always=bool(save.get("always", False)),
                memory_type=save.get("memory_type", ""),
                maat_field=save.get("maat_field", ""),
                priority=save.get("priority"),
            )
            if save.get("always"):
                _store_memory(
                    database,
                    settings,
                    "assistant",
                    save["memory"],
                    layer="keyword",
                    keywords=save.get("keywords", ""),
                    tags=save.get("tags", ""),
                    always=True,
                    memory_type=save.get("memory_type", ""),
                    maat_field=save.get("maat_field", ""),
                    priority=save.get("priority"),
                )
            stored_saves.append(save)
        info["stored_saves"] = stored_saves

    storage_output = _strip_thinking(visible_output)
    _add_working("assistant", storage_output, settings)
    if data.get("supermem_autostore", True):
        if not manual and not saves:
            decision = _autostore_decision("user", user_input, settings)
            info["autostore"].append({"role": "user", **decision})
            if decision.get("store"):
                _store_memory(database, settings, "user", decision["text"], layer="episodic", memory_type=decision.get("memory_type", ""))
        assistant_decision = _autostore_decision("assistant", storage_output, settings)
        info["autostore"].append({"role": "assistant", **assistant_decision})
        if assistant_decision.get("store"):
            _store_memory(database, settings, "assistant", assistant_decision["text"], layer="episodic", memory_type=assistant_decision.get("memory_type", ""))

    if stored_saves and data.get("supermem_show_save_box", True):
        visible_output = f"{visible_output.rstrip()}\n\n{_save_box(stored_saves)}".strip()
    return visible_output, info


def stats(database: Database) -> dict[str, Any]:
    rows = database.connection.execute(
        """
        SELECT layer, COUNT(*) AS count
        FROM supermem_memories
        WHERE status='active'
        GROUP BY layer
        """
    ).fetchall()
    layers = {row["layer"]: int(row["count"]) for row in rows}
    graph = database.connection.execute("SELECT COUNT(*) AS count FROM supermem_person_graph").fetchone()["count"]
    return {
        "working": len(WORKING_MEMORY),
        "layers": layers,
        "person_graph": int(graph),
        **archive_stats(database),
    }


def command_memory(database: Database, settings: Any, args: list[str]) -> str:
    data = _settings(settings)
    if not args:
        s = stats(database)
        return (
            f"MAAT Super Memory: {'on' if data.get('supermem_enabled', True) else 'off'}\n"
            f"User: {data.get('supermem_current_user', 'User')}\n"
            f"Top-K: {data.get('supermem_top_k', 5)} | AutoStore: {'on' if data.get('supermem_autostore', True) else 'off'} | "
            f"AutoRecall: {'on' if data.get('supermem_autorecall', True) else 'off'}\n"
            f"Working: {s['working']} | Layers: {s['layers']} | Person Graph: {s['person_graph']} | "
            f"Archiv: {s.get('monthly_archive', 0)} Monate/{s.get('archived_sources', 0)} Quellen"
        )
    sub = args[0].lower()
    if sub in {"on", "off"}:
        data["supermem_enabled"] = sub == "on"
        return f"MAAT Super Memory {'aktiviert' if data['supermem_enabled'] else 'deaktiviert'}."
    if sub == "debug" and len(args) >= 2:
        data["supermem_debug"] = args[1].lower() in {"on", "true", "1", "ja"}
        return f"Super Memory Debug {'an' if data['supermem_debug'] else 'aus'}."
    if sub == "top" and len(args) >= 2:
        data["supermem_top_k"] = max(1, min(int(args[1]), 20))
        return f"Super Memory Top-K: {data['supermem_top_k']}"
    if sub == "user":
        if len(args) == 1:
            return f"Aktueller Memory-User: {data.get('supermem_current_user', 'User')}"
        if args[1].lower() == "add" and len(args) >= 3:
            name = " ".join(args[2:]).strip()
            known = _split_csv(data.get("supermem_known_users", ""))
            if name and not any(_same_user(name, item) for item in known):
                known.append(name)
            data["supermem_known_users"] = ", ".join(known)
            data["supermem_current_user"] = name or data.get("supermem_current_user", "User")
            return f"User angelegt/ausgewählt: {data['supermem_current_user']}"
        data["supermem_current_user"] = " ".join(args[1:]).strip() or "User"
        return f"Aktueller Memory-User: {data['supermem_current_user']}"
    if sub == "save" and len(args) >= 2:
        text = " ".join(args[1:]).strip()
        _store_memory(database, settings, "user", text, layer="episodic")
        _store_memory(database, settings, "user", text, layer="semantic")
        return f"Gespeichert: {_compress(text, 120)}"
    if sub == "dream":
        hours = None
        if len(args) >= 2:
            try:
                hours = int(args[1])
            except (TypeError, ValueError):
                hours = None
        result = run_memory_dreaming(database, settings, hours=hours)
        return (
            "MAAT Memory Dreaming abgeschlossen.\n"
            f"Zeitraum: {result.get('hours')} Stunden\n"
            f"Quellen: {result.get('source_rows')} | Dreams neu: {result.get('created')} | aktualisiert: {result.get('updated')}\n"
            f"Archiv: {result.get('archive', {}).get('archived', 0)} Erinnerungen in "
            f"{result.get('archive', {}).get('groups', 0)} Gruppen"
        )
    if sub == "archive":
        days = None
        if len(args) >= 2:
            try:
                days = int(args[1])
            except (TypeError, ValueError):
                days = None
        result = archive_old_memories(database, settings, after_days=days)
        return (
            "MAAT Memory Archivierung abgeschlossen.\n"
            f"Schwelle: {result.get('after_days')} Tage | archiviert: {result.get('archived')} | "
            f"Gruppen: {result.get('groups')}"
        )
    if sub == "search" and len(args) >= 2:
        query = " ".join(args[1:])
        items = recall_memories(database, settings, query)
        if not items:
            return f"Keine Erinnerungen zu `{query}` gefunden."
        lines = [f"MAAT Memory Search: `{query}`"]
        for index, item in enumerate(items, 1):
            meta = "/".join(part for part in [item.get("source"), item.get("category"), item.get("memory_type"), item.get("maat_field")] if part)
            lines.append(f"{index}. [{meta}|{float(item.get('score') or 0):.2f}|{_relative_time(item.get('ts'))}] {_compress(item.get('content', ''), 180)}")
        return "\n".join(lines)
    if sub == "graph":
        return command_graph(database, settings, args[1:])
    if sub == "person":
        return command_person(database, settings, args[1:])
    if sub == "timeline":
        return command_timeline(database, settings, args[1:], milestones=False)
    if sub == "milestones":
        return command_timeline(database, settings, args[1:], milestones=True)
    if sub == "stats":
        return json.dumps(stats(database), indent=2, ensure_ascii=False)
    return "Usage: /maat memory [on|off|debug on|off|top <n>|user <name>|user add <name>|save <text>|dream [stunden]|archive [tage]|search <query>|graph|person <name>|timeline|milestones|stats]"


def command_graph(database: Database, settings: Any, args: list[str]) -> str:
    current = _current_user(settings)
    rows = database.connection.execute(
        """
        SELECT *
        FROM supermem_person_graph
        WHERE source_user = ?
        ORDER BY maturity DESC, confidence DESC, evidence_count DESC, updated_at DESC
        LIMIT 40
        """,
        (current,),
    ).fetchall()
    if not rows:
        return f"Person Graph leer für {current}."
    lines = [f"MAAT Person Graph für {current}"]
    for row in rows:
        lines.append(
            f"- {row['target_person']} — {row['relation'] or 'erwähnte Person'} — "
            f"{row['emotion'] or 'neutral'} — {row['maturity']} "
            f"(confidence={float(row['confidence'] or 0):.2f}, evidence={int(row['evidence_count'] or 0)})"
        )
    return "\n".join(lines)


def command_person(database: Database, settings: Any, args: list[str]) -> str:
    if not args:
        return "Usage: /maat person <Name>"
    name = " ".join(args).strip()
    current = _current_user(settings)
    rows = database.connection.execute(
        """
        SELECT *
        FROM supermem_person_graph
        WHERE source_user = ? AND LOWER(target_person) LIKE ?
        ORDER BY confidence DESC, evidence_count DESC
        LIMIT 10
        """,
        (current, f"%{name.lower()}%"),
    ).fetchall()
    memories = _recall_person_memories(database, name, settings, 5)
    lines = [f"MAAT Person: {name}"]
    if rows:
        for row in rows:
            lines.append(
                f"- Graph: {current} -> {row['target_person']} | relation={row['relation']} | "
                f"emotion={row['emotion']} | status={row['relation_status']} | maturity={row['maturity']} | "
                f"confidence={float(row['confidence'] or 0):.2f}"
            )
            if row["last_evidence"]:
                lines.append(f"  Evidenz: {_compress(row['last_evidence'], 180)}")
    else:
        lines.append("- Kein Graph-Eintrag gefunden.")
    if memories:
        lines.append("Erinnerungen:")
        for item in memories:
            lines.append(f"- [{item.get('memory_type')}/{_relative_time(item.get('ts'))}] {_compress(item.get('content', ''), 180)}")
    return "\n".join(lines)


def _milestone_clean_content(content: str) -> str:
    text = str(content or "").strip()
    text = re.sub(r"(?im)^H\s*=\s*[\d.,]+.*?(?:Stability|Maat Value).*?$", "", text)
    text = re.sub(r"(?is)<details[^>]*>.*?</details>", "", text)
    text = re.sub(r"(?is)\bsave\s*:\s*\([^)]{0,900}\)", "", text)
    text = re.sub(r"(?im)^(Hallo|Hey)\s+\w+[!.:,\s]*", "", text).strip()
    return re.sub(r"\s+", " ", text).strip()


def _is_milestone_noise(item: dict[str, Any]) -> bool:
    clean = _norm(_milestone_clean_content(item.get("content", "")))
    if not clean:
        return True
    if len(_tokens(clean)) < 5:
        return True
    noisy = [
        "hallo", "danke", "gern geschehen", "alles klar", "ich teste", "test",
        "kurz gesagt", "wie geht es", "was kann ich", "bereit fuer", "bereit für",
        "copy", "vorlesen", "denken anzeigen",
    ]
    return any(marker in clean for marker in noisy) and not any(
        marker in clean
        for marker in ["gespeichert", "gebaut", "implement", "entscheidung", "projekt", "paper", "formel", "fix"]
    )


def _entry_milestone_score(item: dict[str, Any]) -> float:
    text = _norm(_milestone_clean_content(item.get("content", "")))
    score = 0.0
    memory_type = _norm(item.get("memory_type") or "")
    category = _norm(item.get("category") or "")
    tags = _norm(item.get("tags") or "")
    keywords = _norm(item.get("keywords") or "")
    blob = " ".join([text, memory_type, category, tags, keywords])

    for marker, value in [
        ("meilenstein", 0.32),
        ("entscheidung", 0.25),
        ("beschlossen", 0.22),
        ("implement", 0.22),
        ("eingebaut", 0.20),
        ("gebaut", 0.16),
        ("fertig", 0.16),
        ("fix", 0.16),
        ("paper", 0.18),
        ("formel", 0.18),
        ("projekt", 0.14),
        ("release", 0.20),
        ("architektur", 0.14),
        ("person graph", 0.16),
        ("super memory", 0.15),
        ("web core", 0.16),
    ]:
        if marker in blob:
            score += value

    if memory_type in {"decision", "project", "technical"}:
        score += 0.18
    elif memory_type in {"relationship", "identity"}:
        score += 0.08
    if category in {"projekt", "technik", "meta"}:
        score += 0.08
    if item.get("maat_field") in {"H", "B", "S", "V", "R"}:
        score += 0.03
    try:
        score += max(0.0, min(float(item.get("priority") or 0), 1.0)) * 0.12
        score += max(0.0, min(float(item.get("importance") or 0), 1.0)) * 0.10
        score += max(0.0, min(float(item.get("confidence") or 0), 1.0)) * 0.06
        score += min(int(item.get("hits") or 0), 8) * 0.015
    except (TypeError, ValueError):
        pass
    if _is_milestone_noise(item):
        score -= 0.45
    return round(max(0.0, min(score, 1.6)), 3)


def _milestone_per_day(args: list[str]) -> int:
    for arg in args:
        try:
            return max(1, min(int(arg), 8))
        except (TypeError, ValueError):
            continue
    return 3


def command_timeline(database: Database, settings: Any, args: list[str], milestones: bool = False) -> str:
    per_day = _milestone_per_day(args) if milestones else 6
    limit = 600 if milestones else 120
    rows = database.connection.execute(
        """
        SELECT *
        FROM supermem_memories
        WHERE status='active'
        ORDER BY ts DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    if not rows:
        return "Timeline leer."
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        item = _row_to_item(row)
        if milestones:
            item["milestone_score"] = _entry_milestone_score(item)
            if item["milestone_score"] < 0.52:
                continue
        day = datetime.fromtimestamp(float(item["ts"])).strftime("%Y-%m-%d")
        grouped.setdefault(day, []).append(item)
    if milestones and not grouped:
        for row in rows[:80]:
            item = _row_to_item(row)
            if _is_milestone_noise(item):
                continue
            item["milestone_score"] = _entry_milestone_score(item)
            day = datetime.fromtimestamp(float(item["ts"])).strftime("%Y-%m-%d")
            grouped.setdefault(day, []).append(item)
    title = "MAAT Meilensteine" if milestones else "MAAT Timeline"
    lines = [title]
    for day, items in list(grouped.items())[:14]:
        lines.append(f"**{day}**")
        ranked = sorted(
            items,
            key=lambda item: (
                float(item.get("milestone_score") or 0),
                float(item.get("priority") or 0) + float(item.get("importance") or 0),
            ),
            reverse=True,
        )
        for item in ranked[:per_day]:
            meta = "/".join(part for part in [item.get("category"), item.get("memory_type"), item.get("maat_field")] if part)
            score = f"|m={float(item.get('milestone_score') or 0):.2f}" if milestones else ""
            lines.append(f"- [{meta}{score}] {_compress(_milestone_clean_content(item.get('content', '')), 170)}")
    return "\n".join(lines)
