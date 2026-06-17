from __future__ import annotations

import hashlib
import random
import re
import sqlite3
from datetime import datetime
from typing import Any

from .database import Database, now_iso


LESSON_TYPES = {"positive", "negative", "critical", "style", "fact_check"}
LESSON_CATEGORIES = {
    "smalltalk",
    "coding",
    "philosophy",
    "science",
    "project",
    "memory",
    "style",
    "emotion",
    "symbolism",
    "wissen",
}

LEGACY_CATEGORY_MAP = {
    "allgemein": "wissen",
    "beziehung": "smalltalk",
    "technik": "coding",
    "meta": "style",
    "projekt": "project",
    "symbolik": "symbolism",
}

MATURITY_BONUS = {
    "EXPERIMENTAL": 0.00,
    "PROMISING": 0.10,
    "ESTABLISHED": 0.20,
    "CORE": 0.35,
}

INTERNAL_LESSON_MARKERS = (
    "[MAAT_LOCAL_ONLY]",
    "[MAAT_INTERNAL_CONTEXT_COMPRESSION]",
    "[MAAT_CONTEXT_SUMMARY]",
    "[/MAAT_CONTEXT_SUMMARY]",
    "[MAAT_CHAT_MEMORY]",
    "[MAAT_CHAT_SUMMARY]",
    "[MAAT_ACTIVE_LESSONS]",
)

LAST_WHY: dict[str, Any] = {}
NEXT_HINTS: list[str] = []
LAST_FEEDBACK: dict[str, Any] = {}


def _norm(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _clean_lesson(text: str) -> str:
    lesson = re.sub(r"\s+", " ", str(text or "")).strip(" \t\r\n-:;")
    if len(lesson) > 700:
        lesson = lesson[:697].rstrip() + "..."
    return lesson


def _is_internal_lesson_text(text: str) -> bool:
    raw = str(text or "")
    return any(marker in raw for marker in INTERNAL_LESSON_MARKERS)


def _lesson_key(text: str, category: str = "") -> str:
    core = _norm(text)
    core = re.sub(r"^bei\s+\S+-antworten\s+", "bei antworten ", core)
    core = re.sub(r"\s+", " ", core).strip()
    return hashlib.sha1(f"{category}|{core}".encode("utf-8")).hexdigest()[:16]


def _parse_ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(raw[:19], fmt)
        except ValueError:
            continue
    return None


def _age_days(item: dict[str, Any], now: datetime | None = None) -> float:
    now = now or datetime.now()
    ts = _parse_ts(item.get("timestamp") or item.get("created_at"))
    if not ts:
        return 0.0
    return max(0.0, (now - ts).total_seconds() / 86400.0)


def age_label(item: dict[str, Any]) -> str:
    days = int(round(_age_days(item)))
    if days <= 0:
        return "heute"
    if days == 1:
        return "gestern"
    if days == 2:
        return "vorgestern"
    if days < 7:
        return f"vor {days} Tagen"
    weeks, rest = divmod(days, 7)
    if days < 31:
        return f"vor {weeks} Woche(n)" + (f" und {rest} Tag(en)" if rest else "")
    months, rest = divmod(days, 30)
    if days < 365:
        return f"vor {months} Monat(en)" + (f" und {rest} Tag(en)" if rest else "")
    years, rest = divmod(days, 365)
    return f"vor {years} Jahr(en)" + (f" und {rest} Tag(en)" if rest else "")


def normalize_category(category: str, text: str = "") -> str:
    raw = _norm(category).replace("-", "_")
    raw = LEGACY_CATEGORY_MAP.get(raw, raw)
    if raw in LESSON_CATEGORIES:
        return raw

    low = _norm(text)
    if any(w in low for w in ["code", "python", "script", "pygame", "bug", "fehler", "terminal", "programmieren", "modul"]):
        return "coding"
    if any(w in low for w in ["oma", "opa", "familie", "trauer", "traurig", "gefühle", "gefuehl", "emotional", "vermiss", "angst"]):
        return "emotion"
    if any(w in low for w in ["symbol", "gematria", "zahl", "mona lisa", "da vinci", "vesica", "777"]):
        return "symbolism"
    if any(w in low for w in ["philosophie", "bewusstsein", "theorie", "maat", "respekt", "balance", "jenseits"]):
        return "philosophy"
    if any(w in low for w in ["paper", "projekt", "feedback-tool", "memory", "supermemory", "timeline", "kompressor"]):
        return "project"
    if any(w in low for w in ["markdown", "format", "absatz", "überschrift", "ueberschrift", "emoji", "smiley", "stil"]):
        return "style"
    if any(w in low for w in ["quelle", "fakt", "beweis", "wissenschaft", "evidenz", "daten"]):
        return "science"
    if any(w in low for w in ["hallo", "hi", "hey", "danke", "smalltalk", "smaltalk", "^^", ":d", "xd"]):
        return "smalltalk"
    return "wissen"


def normalize_type(feedback_type: str, lesson: str = "") -> str:
    raw = _norm(feedback_type)
    if raw in LESSON_TYPES:
        return raw
    low = _norm(lesson)
    if any(w in low for w in ["fakt", "evidenz", "beweis", "quelle", "halluzination", "unsicherheit"]):
        return "fact_check"
    if any(w in low for w in ["format", "absatz", "markdown", "stil", "emoji", "ton"]):
        return "style"
    if any(w in low for w in ["falsch", "kritisch", "widersprechen", "nicht nur zustimmen", "behauptung"]):
        return "critical"
    if any(w in low for w in ["gut", "beibehalten", "hilfreich", "passend"]):
        return "positive"
    if any(w in low for w in ["schlecht", "nicht gut", "zu lang", "zu kurz"]):
        return "negative"
    return "critical"


def current_user(settings: Any) -> str:
    return " ".join(str(getattr(settings, "supermem_current_user", "") or "").split())


def lesson_confidence(item: dict[str, Any]) -> float:
    success = float(item.get("success_count", 0) or 0)
    fail = float(item.get("fail_count", 0) or 0)
    return round((success + 1.0) / (success + fail + 2.0), 3)


def lesson_maturity(item: dict[str, Any]) -> str:
    success = int(item.get("success_count", 0) or 0)
    fail = int(item.get("fail_count", 0) or 0)
    total = success + fail
    confidence = lesson_confidence(item)
    age = _age_days(item)
    if total >= 100 and confidence >= 0.90 and age >= 60 and fail <= max(3, int(total * 0.08)):
        return "CORE"
    if total >= 100 and confidence >= 0.80:
        return "ESTABLISHED"
    if total >= 20 and confidence >= 0.70:
        return "PROMISING"
    return "EXPERIMENTAL"


def effective_lesson_score(
    item: dict[str, Any],
    settings: Any,
    context_tone: str = "",
    context_category: str = "",
    active_user: str = "",
) -> float:
    base_score = float(item.get("score", 0.80) or 0.80)
    hits = float(item.get("hits", 0) or 0)
    usage_bonus = min(0.35, hits * float(getattr(settings, "adaptive_learning_usage_bonus", 0.08)))
    maturity_bonus = MATURITY_BONUS.get(lesson_maturity(item), 0.0)
    user_bonus = 0.0
    item_user = _norm(item.get("user", ""))
    if active_user and item_user and item_user == _norm(active_user):
        user_bonus = float(getattr(settings, "adaptive_learning_user_bonus", 0.20))
    age_penalty = _age_days(item) * float(getattr(settings, "adaptive_learning_age_penalty_per_day", 0.006))
    score = lesson_confidence(item) * base_score + maturity_bonus + usage_bonus + user_bonus - age_penalty

    lesson_type = item.get("lesson_type") or item.get("type") or "critical"
    if context_tone == "creative" and lesson_type == "fact_check" and context_category not in {"science", "wissen", "symbolism"}:
        score -= 0.20
    if context_tone == "creative" and lesson_maturity(item) == "EXPERIMENTAL" and lesson_type in {"fact_check", "critical"}:
        score -= 0.08
    return round(max(0.01, score), 3)


def _row_to_item(row: sqlite3.Row | dict[str, Any], settings: Any | None = None) -> dict[str, Any]:
    item = dict(row)
    item["type"] = item.get("lesson_type") or item.get("type") or "critical"
    item["confidence"] = lesson_confidence(item)
    item["maturity"] = lesson_maturity(item)
    item["age"] = age_label(item)
    if settings is not None:
        item["effective_score"] = effective_lesson_score(item, settings)
    return item


def initialize_adaptive_learning(database: Database) -> None:
    database.connection.execute(
        """
        CREATE TABLE IF NOT EXISTS maat_lessons (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'unknown',
            category TEXT NOT NULL DEFAULT 'wissen',
            lesson_type TEXT NOT NULL DEFAULT 'critical',
            lesson TEXT NOT NULL,
            user TEXT NOT NULL DEFAULT '',
            success_count INTEGER NOT NULL DEFAULT 0,
            fail_count INTEGER NOT NULL DEFAULT 0,
            score REAL NOT NULL DEFAULT 0.80,
            hits INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            last_used TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    database.connection.commit()


def store_lesson(
    database: Database,
    lesson: str,
    category: str = "auto",
    lesson_type: str = "critical",
    source: str = "silent_feedback",
    score: float = 0.90,
    user: str = "",
) -> dict[str, Any]:
    clean = _clean_lesson(lesson)
    if _is_internal_lesson_text(clean):
        return {"stored": False, "reason": "internal_context_ignored"}
    if not clean or _word_count(clean) < 4:
        return {"stored": False, "reason": "lesson_too_short"}

    category = normalize_category(category, clean)
    lesson_type = normalize_type(lesson_type, clean)
    lesson_id = _lesson_key(clean, category)
    existing = database.connection.execute("SELECT * FROM maat_lessons WHERE id = ?", (lesson_id,)).fetchone()
    if existing:
        return {"stored": False, "reason": "duplicate", "item": _row_to_item(existing)}

    timestamp = now_iso()
    database.connection.execute(
        """
        INSERT INTO maat_lessons(
            id, timestamp, source, category, lesson_type, lesson, user,
            success_count, fail_count, score, hits, active, last_used, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 0, 1, '', ?, ?)
        """,
        (
            lesson_id,
            timestamp,
            source,
            category,
            lesson_type,
            clean,
            " ".join(str(user or "").split()),
            1 if lesson_type == "positive" else 0,
            float(score),
            timestamp,
            timestamp,
        ),
    )
    database.connection.commit()
    row = database.connection.execute("SELECT * FROM maat_lessons WHERE id = ?", (lesson_id,)).fetchone()
    return {"stored": True, "item": _row_to_item(row)}


def detect_tone(user_input: str, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    style = context.get("maat_style") if isinstance(context, dict) else {}
    if isinstance(style, dict):
        intent = style.get("intent") or ""
        if intent == "technical":
            return "technical"
        if intent == "philosophical":
            return "philosophical"
        if intent == "creative":
            return "creative"
        if intent == "emotional":
            return "emotional"
    low = _norm(user_input)
    if any(w in low for w in ["code", "python", "pygame", "script", "fehler", "programmieren", "loader"]):
        return "technical"
    if any(w in low for w in ["traurig", "oma", "opa", "familie", "trauer", "vermisse", "angst", "freue", "emotion"]):
        return "emotional"
    if any(w in low for w in ["schreibe", "song", "geschichte", "kreativ", "bild", "musik", "design"]):
        return "creative"
    if any(w in low for w in ["wissenschaft", "paper", "beweis", "empirisch", "formel", "physik"]):
        return "scientific"
    if any(w in low for w in ["philosophie", "bewusstsein", "symbolik", "ma'at", "maat", "theorie", "jenseits"]):
        return "philosophical"
    return "casual"


def detect_category(user_input: str, context: dict[str, Any] | None = None) -> str:
    tone = detect_tone(user_input, context)
    if tone == "technical":
        return "coding"
    if tone == "emotional":
        return "emotion"
    if tone == "scientific":
        return "science"
    if tone == "philosophical":
        return "philosophy"
    if tone == "creative":
        low = _norm(user_input)
        if any(w in low for w in ["symbol", "gematria", "zahl", "da vinci", "777"]):
            return "symbolism"
        return "project"
    return normalize_category("auto", user_input)


def list_lessons(database: Database, settings: Any, category: str = "all", limit: int = 30) -> list[dict[str, Any]]:
    raw_category = _norm(category or "all")
    params: list[Any] = []
    where = "WHERE active = 1"
    if raw_category not in {"all", "*"}:
        where += " AND category = ?"
        params.append(normalize_category(raw_category, ""))
    rows = database.connection.execute(
        f"""
        SELECT * FROM maat_lessons
        {where}
        ORDER BY updated_at DESC
        LIMIT 500
        """,
        params,
    ).fetchall()
    items = [_row_to_item(row, settings) for row in rows]
    items.sort(key=lambda item: effective_lesson_score(item, settings), reverse=True)
    return items[: max(1, int(limit))]


def _weighted_sample(
    items: list[dict[str, Any]],
    limit: int,
    settings: Any,
    context_tone: str = "",
    context_category: str = "",
    active_user: str = "",
) -> list[dict[str, Any]]:
    pool = list(items)
    selected: list[dict[str, Any]] = []
    exploration_rate = float(getattr(settings, "adaptive_learning_exploration_rate", 0.25))
    while pool and len(selected) < limit:
        if random.random() < exploration_rate:
            choice = random.choice(pool)
        else:
            weights = [
                max(0.01, effective_lesson_score(item, settings, context_tone, context_category, active_user))
                for item in pool
            ]
            total = sum(weights)
            point = random.random() * total if total > 0 else 0.0
            acc = 0.0
            choice = pool[-1]
            for item, weight in zip(pool, weights):
                acc += weight
                if acc >= point:
                    choice = item
                    break
        selected.append(choice)
        pool = [item for item in pool if item.get("id") != choice.get("id")]
    return selected


def _touch_lessons(database: Database, items: list[dict[str, Any]]) -> None:
    ids = [item.get("id") for item in items if item.get("id")]
    if not ids:
        return
    timestamp = now_iso()
    database.connection.executemany(
        "UPDATE maat_lessons SET hits = hits + 1, last_used = ?, updated_at = ? WHERE id = ?",
        [(timestamp, timestamp, lesson_id) for lesson_id in ids],
    )
    database.connection.commit()


def select_lessons(
    database: Database,
    settings: Any,
    user_input: str,
    context: dict[str, Any] | None = None,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    context = context or {}
    if not bool(getattr(settings, "adaptive_learning_enabled", True)):
        return [], {"enabled": False, "category": "-", "tone": "-"}
    limit = int(limit if limit is not None else getattr(settings, "adaptive_learning_per_turn", 2))
    limit = max(0, min(2, limit))
    if limit <= 0:
        return [], {"enabled": True, "category": "-", "tone": "-", "reason": "limit_zero"}

    category = detect_category(user_input, context)
    tone = detect_tone(user_input, context)
    user = current_user(settings)
    rows = database.connection.execute(
        "SELECT * FROM maat_lessons WHERE active = 1 ORDER BY updated_at DESC LIMIT 800"
    ).fetchall()
    lessons = [_row_to_item(row, settings) for row in rows]
    if not lessons:
        return [], {"enabled": True, "category": category, "tone": tone, "count": 0}

    user_lessons = [item for item in lessons if user and item.get("user") and _norm(item.get("user")) == _norm(user)]
    global_lessons = [item for item in lessons if not item.get("user")]
    category_pool = [item for item in lessons if item.get("category") == category]
    fallback_pool = [item for item in lessons if item.get("category") in {"wissen", "project", "style"}]

    selected: list[dict[str, Any]] = []
    if user_lessons:
        user_category = [item for item in user_lessons if item.get("category") == category]
        selected.extend(_weighted_sample(user_category or user_lessons, 1, settings, tone, category, user))
    if len(selected) < limit and global_lessons:
        pool = [item for item in global_lessons if item.get("category") == category and item not in selected]
        selected.extend(_weighted_sample(pool, 1, settings, tone, category, user))
    if len(selected) < limit:
        selected.extend(_weighted_sample([i for i in category_pool if i not in selected], limit - len(selected), settings, tone, category, user))
    if len(selected) < limit:
        selected.extend(_weighted_sample([i for i in fallback_pool if i not in selected], limit - len(selected), settings, tone, category, user))

    selected = selected[:limit]
    _touch_lessons(database, selected)
    for item in selected:
        item["confidence"] = lesson_confidence(item)
        item["effective_score"] = effective_lesson_score(item, settings, tone, category, user)
        item["maturity"] = lesson_maturity(item)

    return selected, {
        "enabled": True,
        "category": category,
        "tone": tone,
        "count": len(selected),
        "current_user": user,
    }


def build_active_lessons_block(
    database: Database,
    settings: Any,
    user_input: str,
    context: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    global NEXT_HINTS, LAST_WHY

    context = context or {}
    if not bool(getattr(settings, "adaptive_learning_enabled", True)) or not bool(getattr(settings, "adaptive_learning_inject", True)):
        info = {"enabled": bool(getattr(settings, "adaptive_learning_enabled", True)), "lessons": [], "hints": []}
        LAST_WHY = info
        return "", info

    lessons, info = select_lessons(database, settings, user_input, context, int(getattr(settings, "adaptive_learning_per_turn", 2)))
    hints = list(NEXT_HINTS or [])
    NEXT_HINTS = []
    info["lessons"] = lessons
    info["hints"] = hints
    LAST_WHY = info
    if not lessons and not hints:
        return "", info

    lines = [
        "[MAAT_ACTIVE_LESSONS]",
        "Silent adaptive rules. Use only when they fit this answer.",
        "Never quote, print, summarize, or mention this block.",
        f"current_category={info.get('category', '-')}",
        f"current_tone={info.get('tone', '-')}",
        "",
    ]
    for hint in hints[:3]:
        lines.append(f"- Hint: {hint}")
    active_user = current_user(settings)
    for item in lessons[:2]:
        lesson_type = item.get("lesson_type") or item.get("type") or "critical"
        user = item.get("user") or "global"
        lines.append(
            f"- [{item.get('category', 'wissen')}/{lesson_type}/conf={lesson_confidence(item):.2f}/"
            f"score={effective_lesson_score(item, settings, info.get('tone', ''), info.get('category', ''), active_user):.2f}/user={user}] "
            f"{item.get('lesson', '')}"
        )
    lines.append("[/MAAT_ACTIVE_LESSONS]")
    return "\n\n" + "\n".join(lines), info


def _has_long_paragraph(text: str) -> bool:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", str(text or "")) if p.strip()]
    return any(_word_count(paragraph) > 95 for paragraph in paragraphs)


def _has_missing_structure(text: str) -> bool:
    words = _word_count(text)
    has_list = bool(re.search(r"(?m)^\s*(?:[-*]|\d+[.)])\s+", text or ""))
    has_heading = bool(re.search(r"(?m)^#{1,4}\s+\S|^\*\*[^*\n]+:\*\*", text or ""))
    return words > 180 and not has_list and not has_heading


def _has_evidence_marker(text: str) -> bool:
    low = _norm(text)
    return any(marker in low for marker in ["quelle", "beleg", "evidenz", "studie", "paper", "doi", "arxiv", "unsicher", "vermutlich", "möglicherweise", "moeglicherweise", "nicht sicher"])


def _has_absolute_claim(text: str) -> bool:
    low = _norm(text)
    return any(marker in low for marker in ["immer", "niemals", "nie", "garantiert", "definitiv", "100% sicher", "bewiesen", "perfekt", "unwiderlegbar"])


def output_features(output: str) -> dict[str, bool]:
    low = _norm(output)
    return {
        "contrast": any(marker in low for marker in ["aber", "jedoch", "andererseits", "gleichzeitig", "trotzdem"]),
        "uncertainty": any(marker in low for marker in ["könnte", "koennte", "möglicherweise", "moeglicherweise", "vielleicht", "unsicher", "unklar", "vermutlich"]),
        "absolute_claim": _has_absolute_claim(output),
        "evidence_marker": _has_evidence_marker(output),
        "creative_marker": any(marker in low for marker in ["idee", "vorschlag", "beispiel", "lösung", "loesung"]),
        "connection_marker": any(marker in low for marker in ["du", "deine frage", "wir", "kontext", "zusammen"]),
        "long_paragraph": _has_long_paragraph(output),
        "missing_structure": _has_missing_structure(output),
    }


def record_silent_feedback(
    database: Database,
    settings: Any,
    user_input: str,
    output: str,
    engine_eval: dict[str, Any] | None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    global NEXT_HINTS, LAST_FEEDBACK

    if not bool(getattr(settings, "adaptive_learning_enabled", True)):
        LAST_FEEDBACK = {"enabled": False, "stored": [], "hints": []}
        return LAST_FEEDBACK

    context = context or {}
    style = context.get("maat_style") if isinstance(context, dict) else {}
    intent = str((style or {}).get("intent") or "general")
    category = detect_category(user_input, context)
    features = output_features(output)
    hints: list[str] = []
    stored: list[dict[str, Any]] = []

    def score(field: str, default: float = 10.0) -> float:
        try:
            return float((engine_eval or {}).get(field, default) or default)
        except Exception:
            return default

    simple_intents = {"greeting", "simple_answer", "smalltalk"}
    if score("R") < 7.5:
        hints.append("Unsicherheit markieren, Fakten prüfen.")
    if score("B") < 6.0 and intent not in simple_intents:
        hints.append("These kritisch prüfen, nicht nur zustimmen.")
    if score("H") < 6.5:
        hints.append("Kürzer strukturieren, Absätze setzen.")

    user = current_user(settings)
    if features["long_paragraph"] or features["missing_structure"]:
        stored.append(
            store_lesson(
                database,
                "Bei langen Antworten Absätze, Listen und Markdown nutzen.",
                category="style",
                lesson_type="style",
                source="silent_feedback",
                score=0.90,
                user=user,
            )
        )
    if features["absolute_claim"] and not features["evidence_marker"]:
        lesson_type = "fact_check" if category in {"science", "wissen", "symbolism"} else "critical"
        stored.append(
            store_lesson(
                database,
                "Stärke der Behauptung an Evidenz koppeln oder vorsichtiger formulieren.",
                category=category,
                lesson_type=lesson_type,
                source="silent_feedback",
                score=1.00,
                user=user if category in {"smalltalk", "emotion"} else "",
            )
        )

    NEXT_HINTS = hints
    LAST_FEEDBACK = {
        "enabled": True,
        "category": category,
        "intent": intent,
        "features": features,
        "hints": hints,
        "stored": stored,
    }
    return LAST_FEEDBACK


def stats(database: Database, settings: Any) -> dict[str, Any]:
    row = database.connection.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) AS active,
            SUM(CASE WHEN user != '' THEN 1 ELSE 0 END) AS user_specific
        FROM maat_lessons
        """
    ).fetchone()
    return {
        "enabled": bool(getattr(settings, "adaptive_learning_enabled", True)),
        "inject": bool(getattr(settings, "adaptive_learning_inject", True)),
        "per_turn": int(getattr(settings, "adaptive_learning_per_turn", 2)),
        "total": int(row["total"] or 0),
        "active": int(row["active"] or 0),
        "user_specific": int(row["user_specific"] or 0),
        "last_why": LAST_WHY,
        "last_feedback": LAST_FEEDBACK,
    }


def lessons_text(database: Database, settings: Any, category: str = "all", limit: int = 30) -> str:
    lessons = list_lessons(database, settings, category=category, limit=limit)
    normalized = normalize_category(category, "") if category not in {"all", "*"} else "all"
    if not lessons:
        return "Noch keine passenden MAAT Lessons gespeichert."

    lines = [f"# MAAT Lessons{' - ' + normalized if normalized != 'all' else ''}", ""]
    for idx, item in enumerate(lessons, start=1):
        maturity = lesson_maturity(item)
        success = int(item.get("success_count", 0) or 0)
        fail = int(item.get("fail_count", 0) or 0)
        user = f"/user={item.get('user')}" if item.get("user") else ""
        lines.append(
            f"{idx}. [{maturity}/{item.get('category')}/{item.get('lesson_type')}/"
            f"conf={lesson_confidence(item):.2f}/score={effective_lesson_score(item, settings):.2f}/"
            f"ok={success}/fail={fail}/{age_label(item)}{user}] {item.get('lesson', '')}"
        )
    return "\n".join(lines)


def why_text() -> str:
    info = LAST_WHY or {}
    lessons = info.get("lessons") or []
    hints = info.get("hints") or []
    lines = [
        "# MAAT Why",
        "",
        "Kurze Diagnose, keine Gedankenkette.",
        "",
        f"- Kategorie: `{info.get('category') or '-'}`",
        f"- Ton: `{info.get('tone') or '-'}`",
    ]
    if hints:
        lines.extend(["", "## Aktive Hints"])
        lines.extend(f"- {hint}" for hint in hints[:3])
    if lessons:
        lines.extend(["", "## Aktive Lessons"])
        for idx, item in enumerate(lessons[:2], start=1):
            lines.append(
                f"{idx}. [{item.get('category')}/{item.get('lesson_type')}/conf={lesson_confidence(item):.2f}] "
                f"{item.get('lesson', '')}"
            )
    if not hints and not lessons:
        lines.append("- Keine aktiven Lessons oder Hints im letzten Prompt.")
    return "\n".join(lines)


def command_lessons(database: Database, settings: Any, args: list[str]) -> str:
    if not args:
        return lessons_text(database, settings)
    raw = str(args[0]).lower()
    if raw in {"on", "off"}:
        setattr(settings, "adaptive_learning_enabled", raw == "on")
        return f"MAAT Adaptive Learning {'aktiviert' if raw == 'on' else 'deaktiviert'}."
    if raw in {"inject", "injection"} and len(args) >= 2:
        enabled = str(args[1]).lower() in {"on", "true", "1", "ja", "an"}
        setattr(settings, "adaptive_learning_inject", enabled)
        return f"Adaptive-Learning-Injection {'an' if enabled else 'aus'}."
    if raw in {"top", "limit"} and len(args) >= 2:
        try:
            value = max(0, min(2, int(args[1])))
        except ValueError:
            value = 2
        setattr(settings, "adaptive_learning_per_turn", value)
        return f"Adaptive Lessons pro Antwort: {value}."
    if raw == "clear":
        return "Lesson-Clear ist deaktiviert, damit nicht versehentlich dein Lerngedächtnis gelöscht wird."
    if raw == "add":
        joined = " ".join(args[1:]).strip()
        match = re.match(r"([^|]+)\|([^|]+)\|(.+)$", joined, flags=re.DOTALL)
        if not match:
            return "Format: `/maat lessons add <category>|<type>|<lesson>`"
        category, lesson_type, lesson = (part.strip() for part in match.groups())
        result = store_lesson(
            database,
            lesson,
            category=category,
            lesson_type=lesson_type,
            source="command",
            score=1.0,
            user=current_user(settings),
        )
        if result.get("stored"):
            item = result.get("item") or {}
            return f"MAAT Lesson gespeichert: [{item.get('category')}/{item.get('lesson_type')}] {item.get('lesson')}"
        item = result.get("item") or {}
        if result.get("reason") == "duplicate" and item:
            return f"Lesson bereits vorhanden: [{item.get('category')}/{item.get('lesson_type')}] {item.get('lesson')}"
        return f"Lesson nicht gespeichert: {result.get('reason', 'unknown')}"
    if raw == "stats":
        data = stats(database, settings)
        return (
            "# MAAT Lessons Stats\n\n"
            f"- Enabled: `{data['enabled']}`\n"
            f"- Inject: `{data['inject']}`\n"
            f"- Pro Antwort: `{data['per_turn']}`\n"
            f"- Lessons: `{data['active']}` aktiv / `{data['total']}` gesamt\n"
            f"- User-spezifisch: `{data['user_specific']}`"
        )
    return lessons_text(database, settings, category=args[0])
