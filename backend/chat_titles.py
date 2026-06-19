from __future__ import annotations

import re
from typing import Any


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


TITLE_STOPWORDS = {
    "aber",
    "alle",
    "alles",
    "also",
    "auch",
    "bei",
    "bin",
    "bitte",
    "chat",
    "danke",
    "dann",
    "das",
    "dass",
    "den",
    "der",
    "die",
    "dir",
    "doch",
    "ein",
    "eine",
    "einen",
    "einer",
    "er",
    "es",
    "für",
    "ganz",
    "geht",
    "genau",
    "habe",
    "hallo",
    "hier",
    "ich",
    "ist",
    "jetzt",
    "kann",
    "kannst",
    "kommt",
    "mal",
    "man",
    "meine",
    "mein",
    "mir",
    "mit",
    "noch",
    "nicht",
    "nun",
    "oder",
    "schon",
    "sein",
    "sich",
    "sie",
    "soll",
    "so",
    "und",
    "uns",
    "von",
    "was",
    "wenn",
    "wie",
    "wieder",
    "wir",
    "wird",
    "wo",
    "zu",
    "zum",
    "zur",
}

TITLE_LEADING_RE = re.compile(
    r"^(?:"
    r"hallo|hey|hi|guten morgen|guten abend|danke|perfekt|okay|ok|"
    r"kannst du|können wir|koennen wir|bitte|baue bitte|baue|bau|"
    r"mach bitte|mach|mache|füge|fuege|setze|prüfe|pruefe|schau mal|"
    r"gib mal|gib mir|ich möchte|ich moechte|ich will|lass uns|"
    r"und|so|nun|jetzt|noch|mal"
    r")\b[\s,:;-]*",
    re.I,
)
TITLE_NOISE_RE = re.compile(
    r"<think>.*?</think>|"
    r"```[\s\S]*?```|"
    r"<details[\s\S]*?</details>|"
    r"\[(?:MAAT_INTERNAL|MAAT_THINKING|MAAT_ACTIVE_LESSONS|MAAT_CHAT_MEMORY)[^\]]*\][\s\S]*?\[/[A-Z_]+\]",
    re.I,
)
TITLE_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9_+.#/-]{2,}")
TITLE_HINTS = [
    (
        re.compile(r"\b(?:chatbeschrift|chat[- ]?titel|chat.*beschrift|titel.*chat)", re.I),
        "Chatbeschriftung aus Inhalt",
    ),
    (
        re.compile(r"\bmemory\b|\berinner", re.I),
        "Memory-Fixes",
    ),
    (
        re.compile(r"\b(?:settings|einstellungen).*\bstreaming\w*|\bstreaming\w*.*\b(?:settings|einstellungen)", re.I),
        "Settings während Streaming sperren",
    ),
    (
        re.compile(r"\b(?:think|thinking|denken)\b", re.I),
        "Thinking-Steuerung",
    ),
    (
        re.compile(r"\b(?:modellwechsel|modell[- ]?wechsel)\b", re.I),
        "Modellwechsel verbessern",
    ),
]


def _clean_title_source(text: str) -> str:
    value = visible_message_text(str(text or ""))
    value = TITLE_NOISE_RE.sub(" ", value)
    value = re.sub(r"save:\s*\([^)]*\)", " ", value, flags=re.I)
    value = re.sub(r"\bH\s*=\s*\d+(?:[.,]\d+)?\s+B\s*=\s*\d+(?:[.,]\d+)?[\s\S]*?(?:\n|$)", " ", value)
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[\*_`>#|]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _strip_title_leading_words(text: str) -> str:
    value = str(text or "").strip()
    for _ in range(4):
        cleaned = TITLE_LEADING_RE.sub("", value).strip()
        if cleaned == value:
            break
        value = cleaned
    return value


def _title_candidates(text: str) -> list[str]:
    clean = _clean_title_source(text)
    if not clean:
        return []
    chunks = re.split(r"(?:[.!?]\s+|\n+|;+\s+)", clean)
    candidates: list[str] = []
    for chunk in chunks:
        value = _strip_title_leading_words(chunk)
        value = re.sub(r"\b(?:xD|XD|\^\^|:D|:\)|;\))\b", " ", value)
        value = re.sub(r"\s+", " ", value).strip(" .,;:-–—")
        if len(value) < 6:
            continue
        words = value.split()
        if len(words) > 10:
            value = " ".join(words[:10]).rstrip(" .,;:-–—")
        candidates.append(value)
    return candidates


def _score_title_candidate(text: str, recency_bonus: float = 0.0) -> float:
    words = [match.group(0).lower() for match in TITLE_WORD_RE.finditer(text)]
    meaningful = [word for word in words if word not in TITLE_STOPWORDS and not word.isdigit()]
    if not meaningful:
        return -20.0
    score = len(meaningful) * 2.0 + recency_bonus
    lower = text.lower()
    if any(token in lower for token in ("fix", "fehler", "bug", "public repo", "memory", "modell", "settings", "chat", "titel")):
        score += 3.0
    if lower in {"hallo", "hey", "hi"} or lower.startswith(("hallo ", "hey ", "hi ")):
        score -= 8.0
    if len(text) > 80:
        score -= 1.5
    return score


def _format_chat_title(text: str, fallback: str) -> str:
    value = str(text or "").strip(" .,;:-–—")
    value = re.sub(r"\s+", " ", value)
    if not value:
        return fallback
    words = value.split()
    if len(words) > 8:
        value = " ".join(words[:8]).strip(" .,;:-–—")
    if len(value) > 78:
        value = value[:78].rsplit(" ", 1)[0].strip(" .,;:-–—")
    if value and value[0].islower():
        value = value[:1].upper() + value[1:]
    return value or fallback


def _hint_title(text: str) -> str:
    clean = _clean_title_source(text)
    if not clean:
        return ""
    for pattern, label in TITLE_HINTS:
        if pattern.search(clean):
            if re.search(r"\bpublic repo\b|\böffentlich", clean, flags=re.I):
                return f"{label} im Public Repo"
            return label
    return ""


def smart_chat_title_from_text(text: str, fallback: str = "Neuer Chat") -> str:
    hinted = _hint_title(text)
    if hinted:
        return _format_chat_title(hinted, fallback)
    candidates = _title_candidates(text)
    if not candidates:
        return fallback
    best = max(candidates, key=_score_title_candidate)
    if _score_title_candidate(best) < 0:
        return fallback
    return _format_chat_title(best, fallback)


def smart_chat_title_from_messages(messages: list[dict[str, Any]], fallback: str = "MAAT Chat") -> str:
    scored: list[tuple[float, str]] = []
    user_messages = [item for item in messages if str(item.get("role") or "") == "user"]
    joined_recent = "\n".join(str(item.get("content") or "") for item in user_messages[-4:])
    hinted = _hint_title(joined_recent)
    if hinted:
        return _format_chat_title(hinted, fallback)
    for index, item in enumerate(user_messages[-8:]):
        recency_bonus = index * 0.75
        for candidate in _title_candidates(str(item.get("content") or "")):
            scored.append((_score_title_candidate(candidate, recency_bonus), candidate))
    if not scored:
        return fallback
    score, best = max(scored, key=lambda item: item[0])
    if score < 0:
        return fallback
    return _format_chat_title(best, fallback)
