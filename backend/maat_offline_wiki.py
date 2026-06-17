from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional dependency
    BeautifulSoup = None

try:
    from libzim.reader import Archive
    from libzim.search import Query, Searcher
except Exception:  # pragma: no cover - optional dependency
    Archive = None
    Query = None
    Searcher = None


DEFAULT_ZIM = (
    ""
)

SESSION: dict[str, Any] = {
    "archive_path": None,
    "archive": None,
    "searcher": None,
    "last_terms": [],
    "last_titles": [],
    "last_hit": False,
    "last_error": None,
    "last_ts": None,
}

STOPWORDS = {
    "ich", "du", "wir", "ihr", "sie", "er", "es", "der", "die", "das",
    "ein", "eine", "einen", "einem", "einer", "und", "oder", "aber", "ist",
    "sind", "war", "waren", "hat", "haben", "was", "wer", "wie", "wo",
    "wann", "warum", "bitte", "mir", "dir", "mich", "dich", "zu", "zur",
    "zum", "von", "über", "ueber", "mit", "für", "fuer", "im", "in", "am",
    "an", "auf", "nach", "den", "dem", "des", "hallo", "hi", "hey", "mmh",
    "mhm", "ja", "nein", "ok", "okay", "danke", "jetzt", "mein", "meine",
    "dein", "deine", "kann", "kannst", "können", "koennen", "erkläre",
    "erklaere", "beschreibe", "definition", "infos", "informationen",
    "maat_attachment",
    "bin", "bist", "seid", "wird", "wurde", "muss", "musst", "müssen", "muessen",
    "wieso", "weshalb", "the", "a", "and", "or", "what", "who", "how", "why",
    "please", "about", "tell", "explain", "servus", "moin", "grüß", "gruess",
    "ähm", "aehm", "ehm", "hm", "hmm", "richtig", "kenne", "kennt", "auch",
    "meinung", "dazu", "darüber", "darueber", "sage", "sagen", "erzähl",
    "erzaehl", "erzähle", "erzaehle", "erzählen", "erzaehlen", "mach", "mache",
    "machen", "bau", "baue", "bauen", "erstelle", "erstellen", "generiere",
    "generieren", "berechne", "berechnen", "bestimme", "ermittle", "maß", "mass",
    "maatwert", "wert", "viele", "einwohner", "bewohner", "menschen", "population",
    "weiß", "weis", "nicht", "macht", "sich", "sowas", "gedanken", "denke",
    "doch", "stimmt", "trainiert", "worden", "möchte", "moechte", "will",
    "fahren", "fahre", "fährst", "faehrst", "fahrt", "auto", "route", "reise",
    "spiele", "spiel", "spielst", "spielen", "gespielt", "zocke", "zockst", "zocken",
    "gerne", "gern", "liebe", "mag", "vergleich", "vergleiche", "vergleichen",
    "unterschied", "unterschiede", "gemeinsam", "besser", "schlechter", "ähnlich",
    "aehnlich", "suche", "suchst", "suchen", "gesucht", "finde", "finden",
}

NON_WIKI_CONTEXT_BLOCKS = [
    re.compile(r"\[MAAT_FILE_BUILDER_TEST_LOG\].*?\[/MAAT_FILE_BUILDER_TEST_LOG\]", flags=re.I | re.S),
]

PATTERNS = [
    r"^(?:!wiki|!wikipedia)\s+(.+)$",
    r"^/maat\s+wiki\s+(?!on$|off$|status$|auto\b|path\b|test\b)(.+)$",
    r"\b(?:was ist|wer ist|was bedeutet|bedeutung von|definition von)\s+(.+)$",
    r"\b(?:erkläre|erklaere|definiere|beschreibe)\s+(?:mir\s+)?(.+)$",
    r"\b(?:infos?|informationen|wissen)\s+(?:zu|über|ueber|von)\s+(.+)$",
    r"\b(?:was\s+)?(?:weißt|weisst|weist|weis)\s+du\s+(?:über|ueber|zu|von)\s+(.+?)(?:[?.!]|$)",
    r"\bwas\s+sagst\s+du\s+(?:zu|zur|zum|über|ueber|von)\s+(.+?)(?:[?.!]|$)",
    r"\bwas\s+hältst\s+du\s+(?:von|über|ueber|zur|zum)\s+(.+)$",
    r"\b(?:kennst\s+du|kannst\s+du(?:\s+mir)?(?:\s+(?:was|etwas|mehr|kurz))?\s+(?:über|ueber|zu|von))\s+(.+)$",
    r"\b(?:what is|who is|define|explain|information about)\s+(.+)$",
]


def _settings(settings: Any) -> dict[str, Any]:
    if isinstance(settings, dict):
        return settings
    try:
        return vars(settings)
    except TypeError:
        return {}


def _flag(settings: Any, name: str, default: bool) -> bool:
    return bool(_settings(settings).get(name, default))


def _value(settings: Any, name: str, default: Any) -> Any:
    return _settings(settings).get(name, default)


def _log(settings: Any, *parts: Any) -> None:
    if _flag(settings, "offline_wiki_log", True) or _flag(settings, "offline_wiki_debug", False):
        print("[MAAT Web Core][offline_wiki]", *parts, flush=True)


def _norm_spaces(text: str) -> str:
    text = re.sub(r"(?<!\s)(?:\^\^|[xX][dD]+)\s*", " ", text or "")
    return re.sub(r"\s+", " ", text.strip())


def strip_non_wiki_context(text: str) -> str:
    cleaned = str(text or "")
    for pattern in NON_WIKI_CONTEXT_BLOCKS:
        cleaned = pattern.sub(" ", cleaned)
    return cleaned.strip()


def _strip_attachment_blocks(text: str) -> str:
    value = str(text or "")
    value = re.sub(
        r"\[MAAT_ATTACHMENT[^\]]*\].*?\[/MAAT_ATTACHMENT\]",
        " ",
        value,
        flags=re.DOTALL | re.IGNORECASE,
    )
    value = re.sub(r"\[/?MAAT_ATTACHMENT[^\]]*\]", " ", value, flags=re.IGNORECASE)
    return value


def _clean_term(term: str) -> str:
    term = _strip_attachment_blocks(term)
    term = strip_non_wiki_context(term)
    term = _norm_spaces(term)
    term = re.split(r"[?!]\s+", term, maxsplit=1)[0]
    term = re.sub(r"\s+[:;=xX]-?[dDpP)(]+$", "", term)
    term = re.sub(r"^[\"'`´“”„‚\s]+|[\"'`´“”„‚\s?.!,;:]+$", "", term)
    term = re.sub(r"[\s\^~_*#=+\\/|<>()[\]{}]+$", "", term)
    term = re.sub(
        r"^(?:ein|eine|einen|einem|einer|der|die|das|von|aus|nach|in|zu|zur|zum|über|ueber|"
        r"mein|meine|meiner|meinem|meinen|meines|dein|deine|deiner|deinem|deinen|deines)\s+",
        "",
        term,
        flags=re.I,
    )
    while True:
        cleaned = re.sub(
            r"^(?:aber|doch|auch|ja|nein|ok|okay|mmh|mhm|ähm|aehm|ehm|hm|hmm|halt|eigentlich)\s+",
            "",
            term,
            flags=re.I,
        )
        if cleaned == term:
            break
        term = cleaned
    term = re.sub(r"\bformel\s*1\b", "Formel 1", term, flags=re.I)
    term = re.sub(r"\bbuckelwahl\b", "Buckelwal", term, flags=re.I)
    term = re.sub(r"\bleonrado\b", "Leonardo", term, flags=re.I)
    term = re.sub(r"\b(?:bitte|kurz|einfach|genau|eigentlich)\b", " ", term, flags=re.I)
    term = re.sub(r"\b(?:meine|mein)\s+ich\b.*$", "", term, flags=re.I)
    term = re.sub(r"\b(?:geschrieben|verfasst|gemacht|erstellt|gedacht)\b.*$", "", term, flags=re.I)
    term = re.sub(r"\b(?:erklären|erklaeren|beschreiben|sagen|geben)\b.*$", "", term, flags=re.I)
    term = re.sub(r"\b(?:ist|sind|war|waren|heißt|heisst)\b.*$", "", term, flags=re.I)
    term = re.sub(r"\s+(?:nicht|noch\s+nicht|gar\s+nicht|auch\s+nicht)$", "", term, flags=re.I)
    term = re.sub(
        r"\s+(?:gemeinsam|im\s+vergleich|verglichen|vergleichen|unterschiede?|besser|schlechter|ähnlich|aehnlich|vs\.?|versus)$",
        "",
        term,
        flags=re.I,
    )
    aliases = {
        "formel1": "Formel 1",
        "formel 1": "Formel 1",
        "openai": "OpenAI",
        "leonardo da vinci": "Leonardo da Vinci",
        "marteria": "Marteria",
        "suno ai": "Suno",
        "suno.com": "Suno",
        "musik": "Musik",
        "music": "Musik",
        "äpfel": "Apfel",
        "aepfel": "Apfel",
        "birnen": "Birne",
    }
    normalized = _norm_spaces(term)
    return aliases.get(normalized.lower(), normalized)


def _apply_role_hint(term: str, raw: str) -> str:
    term_low = (term or "").strip().lower()
    if term_low in {"suno", "suno ai", "suno.com"}:
        return "Suno"
    if term_low in {"formel1", "formel 1"}:
        return "Formel 1"
    return term


def _valid_term(term: str, settings: Any) -> bool:
    min_len = int(_value(settings, "offline_wiki_min_term_len", 3) or 3)
    lowered = term.lower().strip()
    return bool(term and len(term) >= min_len and lowered not in STOPWORDS and not lowered.startswith("maat_attachment"))


def _append_term(terms: list[str], term: str, raw: str, settings: Any) -> None:
    cleaned = _apply_role_hint(_clean_term(term), raw)
    if not _valid_term(cleaned, settings):
        return
    if cleaned.lower() not in {item.lower() for item in terms}:
        terms.append(cleaned)


def _creative_request_term(raw: str) -> str | None:
    lowered = (raw or "").lower()
    creative_intent = re.search(
        r"\b(?:schreib(?:e|en|st)?|mach(?:e|en|st)?|bau(?:e|en|st)?|erstelle(?:n|st)?|dichte|komponiere)\b",
        lowered,
    )
    if not creative_intent:
        return None
    if re.search(r"\b(?:song|lied|songs|lieder)\b", lowered):
        return "Song"
    if re.search(r"\b(?:gedicht|poem|poesie)\b", lowered):
        return "Gedicht"
    if re.search(r"\b(?:rap|rappertext|raptext)\b", lowered):
        return "Rap"
    return None


def _music_creation_terms(raw: str) -> list[str]:
    lowered = (raw or "").lower()
    has_music = re.search(r"\b(?:musik|music|song|songs|lied|lieder|track|tracks)\b", lowered)
    has_creation = re.search(
        r"\b(?:erstellt|gemacht|gebaut|generiert|komponiert|produziert|erstelle|machen|baue|generiere|komponiere|produziere)\b",
        lowered,
    )
    if not has_music:
        return []
    terms: list[str] = []
    if re.search(r"\b(?:suno|suno\s+ai|suno\.com)\b", lowered):
        terms.append("Suno")
    if has_creation or terms:
        terms.append("Musik")
    return terms


def _titlecase_candidates(raw: str) -> list[str]:
    out: list[str] = []
    tokens = re.findall(r"\b[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9_-]{2,}\b", raw or "")
    for token in tokens:
        if token.lower() not in STOPWORDS and token not in out:
            out.append(token)
    return out


def _route_terms(raw: str, settings: Any) -> list[str]:
    terms: list[str] = []
    route_patterns = [
        r"\b(?:von|aus)\s+(.+?)\s+(?:nach|in|zur|zum|zu|bis)\s+(.+?)(?:[?.!;:]|$)",
        r"\bzwischen\s+(.+?)\s+und\s+(.+?)(?:[?.!;:]|$)",
    ]
    for pattern in route_patterns:
        match = re.search(pattern, raw, flags=re.I)
        if not match:
            continue
        _append_term(terms, match.group(1), raw, settings)
        _append_term(terms, match.group(2), raw, settings)
        if len(terms) >= 2:
            break
    return terms


def _paired_terms(raw: str, settings: Any) -> list[str]:
    terms: list[str] = []
    if _creative_request_term(raw) or _music_creation_terms(raw):
        return terms
    pair_patterns = [
        r"\b(?:vergleiche|vergleich|unterschiede?)\s+(.+?)\s+(?:mit|zu|gegen|gegenüber|gegenueber)\s+(.+?)(?:[?.!;:]|$)",
        r"\b(?:vergleiche|vergleich\s+(?:von|zwischen)?|unterschiede?\s+(?:zwischen|von)?|was\s+haben)\s+(.+?)\s+und\s+(.+?)(?:\s+gemeinsam)?(?:[?.!;:]|$)",
        r"\b(.+?)\s+(?:vs\.?|versus|oder)\s+(.+?)(?:[?.!;:]|$)",
        r"\b(.+?)\s+im\s+vergleich\s+(?:zu|mit)\s+(.+?)(?:[?.!;:]|$)",
    ]
    for pattern in pair_patterns:
        match = re.search(pattern, raw, flags=re.I)
        if not match:
            continue
        _append_term(terms, match.group(1), raw, settings)
        _append_term(terms, match.group(2), raw, settings)
        if len(terms) >= 2:
            break
    return terms


def extract_main_terms(text: str, settings: Any) -> list[str]:
    raw = _norm_spaces(strip_non_wiki_context(_strip_attachment_blocks(text)))
    if not raw:
        return []
    max_terms = max(1, min(int(_value(settings, "offline_wiki_max_terms", 2) or 2), 4))
    terms: list[str] = []

    for term in _music_creation_terms(raw):
        _append_term(terms, term, raw, settings)
        if len(terms) >= max_terms:
            return terms
    if terms:
        return terms[:max_terms]

    creative_term = _creative_request_term(raw)
    if creative_term:
        _append_term(terms, creative_term, raw, settings)
        return terms[:max_terms]

    pair_patterns = [
        r"\b(?:vergleiche|vergleich|unterschiede?)\s+(.+?)\s+(?:mit|zu|gegen|gegenüber|gegenueber)\s+(.+?)(?:[?.!;:]|$)",
        r"\b(.+?)\s+(?:vs\.?|versus)\s+(.+?)(?:[?.!;:]|$)",
    ]
    for pattern in pair_patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            _append_term(terms, match.group(1), raw, settings)
            _append_term(terms, match.group(2), raw, settings)
            return terms[:max_terms]

    for term in _paired_terms(raw, settings):
        _append_term(terms, term, raw, settings)
        if len(terms) >= max_terms:
            return terms

    for term in _route_terms(raw, settings):
        _append_term(terms, term, raw, settings)
        if len(terms) >= max_terms:
            return terms

    for pattern in PATTERNS:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            _append_term(terms, match.group(1), raw, settings)
            return terms[:max_terms]

    for candidate in _titlecase_candidates(raw):
        _append_term(terms, candidate, raw, settings)
        if terms:
            return terms[:max_terms]

    return []


def _zim_path(settings: Any) -> str:
    raw = str(_value(settings, "offline_wiki_zim_path", DEFAULT_ZIM) or DEFAULT_ZIM)
    return os.path.abspath(os.path.expanduser(raw))


def reset_archive() -> None:
    SESSION["archive"] = None
    SESSION["searcher"] = None
    SESSION["archive_path"] = None


def _open_archive(settings: Any):
    if Archive is None:
        SESSION["last_error"] = "libzim ist nicht installiert."
        return None

    path = _zim_path(settings)
    if not os.path.exists(path):
        SESSION["last_error"] = f"ZIM nicht gefunden: {path}"
        return None

    if SESSION.get("archive") is not None and SESSION.get("archive_path") == path:
        return SESSION["archive"]

    archive = Archive(path)
    SESSION["archive"] = archive
    SESSION["archive_path"] = path
    SESSION["searcher"] = Searcher(archive) if Searcher is not None else None
    SESSION["last_error"] = None
    return archive


def _candidate_titles(term: str) -> list[str]:
    cleaned = _clean_term(term)
    variants = [
        cleaned,
        cleaned.replace("_", " "),
        cleaned.replace(" ", "_"),
        cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned,
        cleaned.title(),
    ]
    out: list[str] = []
    for item in variants:
        if item and item not in out:
            out.append(item)
    return out


def _entry_by_title_or_path(archive: Any, term: str):
    for title in _candidate_titles(term):
        try:
            return archive.get_entry_by_title(title)
        except Exception:
            pass
        try:
            return archive.get_entry_by_path(title.replace(" ", "_"))
        except Exception:
            pass
    return None


def _entry_by_search(archive: Any, term: str):
    searcher = SESSION.get("searcher")
    if searcher is None or Query is None:
        return None
    try:
        result = searcher.search(Query().set_query(term))
        paths = list(result.getResults(0, 8))
    except Exception:
        return None

    fallback = None
    for path in paths:
        try:
            entry = archive.get_entry_by_path(path)
        except Exception:
            continue
        title = getattr(entry, "title", "") or ""
        if "begriffsklärung" not in title.lower():
            return entry
        fallback = fallback or entry
    return fallback


def _html_to_text(content: bytes | str) -> str:
    raw = content.decode("utf-8", "ignore") if isinstance(content, (bytes, bytearray)) else str(content or "")
    if BeautifulSoup is None:
        raw = re.sub(r"<script\b.*?</script>", " ", raw, flags=re.I | re.S)
        raw = re.sub(r"<style\b.*?</style>", " ", raw, flags=re.I | re.S)
        raw = re.sub(r"<[^>]+>", " ", raw)
        return _norm_spaces(raw)

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "nav", "table", "sup", "footer"]):
        tag.decompose()
    return _norm_spaces(soup.get_text(" ", strip=True))


def lookup(term: str, settings: Any) -> tuple[dict[str, str] | None, bool]:
    archive = _open_archive(settings)
    if archive is None:
        return None, False

    entry = _entry_by_title_or_path(archive, term) or _entry_by_search(archive, term)
    if entry is None:
        SESSION["last_error"] = f"Kein Offline-Wiki-Treffer für: {term}"
        return None, False

    try:
        item = entry.get_item()
        text = _html_to_text(bytes(item.content))
    except Exception as exc:
        SESSION["last_error"] = f"Artikel konnte nicht gelesen werden: {exc}"
        return None, False

    max_chars = int(_value(settings, "offline_wiki_max_chars", 1400) or 1400)
    title = getattr(entry, "title", "") or term
    path = getattr(entry, "path", "") or title
    source = f"zim://{Path(_zim_path(settings)).name}/{path}"
    return {
        "term": term,
        "title": title,
        "path": path,
        "source": source,
        "text": text[:max_chars].strip(),
    }, True


def _context_block(hit: dict[str, str], index: int, total: int) -> str:
    prefix = f"Kontext {index}/{total}\n" if total > 1 else ""
    return (
        "[MAAT_OFFLINE_WIKI]\n"
        "Interner Faktenkontext. Nicht als Block ausgeben.\n"
        "Quelle: lokale Offline-Wikipedia-ZIM, keine Websuche.\n"
        f"{prefix}"
        f"Suchbegriff: {hit['term']}\n"
        f"Artikel: {hit['title']}\n"
        f"Pfad: {hit['source']}\n\n"
        "Auszug:\n"
        f"{hit['text']}\n\n"
        "Regeln:\n"
        "- Nutze diesen Auszug als Faktenanker.\n"
        "- Wenn du Fakten aus diesem Block nutzt, behandle ihre Herkunft als Offline-Wiki-Kontext.\n"
        "- Wenn der User fragt, ob du Wiki-Kontext bekommen hast, antworte klar: Ja, aus der lokalen Offline-Wikipedia-ZIM.\n"
        "- Sage dann nicht, diese Daten kämen nur aus Training oder Live-Web. Offline-Wiki ist kein Browser und kein SuperMemory.\n"
        "- Wenn der Auszug nicht zur Frage passt, sage das klar.\n"
        "- Erfinde keine Details, die nicht im Auszug oder sicherem Kontext stehen.\n"
        "[/MAAT_OFFLINE_WIKI]"
    )


def build_wiki_prompt(settings: Any, user_input: str) -> tuple[str, dict[str, Any]]:
    info = {
        "enabled": _flag(settings, "offline_wiki_enabled", False),
        "terms": [],
        "hits": [],
        "errors": [],
    }
    if not info["enabled"]:
        return "", info

    text = _strip_attachment_blocks(str(user_input or "")).strip()
    explicit = bool(re.match(r"\s*(?:!wiki|!wikipedia|/maat\s+wiki\s+)", text, flags=re.I))
    if not explicit and not _flag(settings, "offline_wiki_auto", True):
        return "", info

    terms = extract_main_terms(text, settings)
    info["terms"] = terms
    if not terms:
        return "", info

    hits: list[dict[str, str]] = []
    errors: list[str] = []
    lookup_settings = _settings(settings).copy()
    if len(terms) >= 2:
        lookup_settings["offline_wiki_max_chars"] = int(_value(settings, "offline_wiki_multi_max_chars", 700) or 700)

    seen_paths: set[str] = set()
    for term in terms:
        hit, ok = lookup(term, lookup_settings)
        if not ok or not hit:
            error = SESSION.get("last_error") or f"Kein Treffer für: {term}"
            errors.append(error)
            _log(settings, f"MISS term={term!r} error={error!r}")
            continue
        key = (hit.get("path") or hit.get("title") or term).lower()
        if key in seen_paths:
            continue
        seen_paths.add(key)
        hits.append(hit)
        _log(settings, f"HIT term={term!r} title={hit['title']!r}")

    info["hits"] = hits
    info["errors"] = errors
    SESSION["last_terms"] = terms
    SESSION["last_titles"] = [hit["title"] for hit in hits]
    SESSION["last_hit"] = bool(hits)
    SESSION["last_error"] = "; ".join(errors) if errors else None
    SESSION["last_ts"] = time.time()

    if not hits:
        return "", info

    source_header = (
        "[MAAT_CONTEXT_SOURCE_STATUS]\n"
        "Offline-Wiki-Kontext ist in diesem Turn AKTIV.\n"
        "Herkunft: lokale Offline-Wikipedia-ZIM, nicht Live-Web, nicht Training, nicht SuperMemory.\n"
        "Wenn der User nach der Herkunft fragt, sage transparent, dass diese Fakten aus dem Offline-Wiki-Kontext kommen.\n"
        "Aktive Artikel: "
        + ", ".join(hit.get("title") or hit.get("term") or "-" for hit in hits)
        + "\n"
        "[/MAAT_CONTEXT_SOURCE_STATUS]"
    )
    blocks = [_context_block(hit, index + 1, len(hits)) for index, hit in enumerate(hits)]
    return "\n\n" + source_header + "\n\n" + "\n\n".join(blocks), info


def status_text(settings: Any) -> str:
    path = _zim_path(settings)
    exists = os.path.exists(path)
    terms = ", ".join(SESSION.get("last_terms") or []) or "-"
    titles = ", ".join(SESSION.get("last_titles") or []) or "-"
    return (
        f"Offline Wiki: {'on' if _flag(settings, 'offline_wiki_enabled', False) else 'off'} | "
        f"auto={'on' if _flag(settings, 'offline_wiki_auto', True) else 'off'} | "
        f"libzim={'ok' if Archive is not None else 'fehlt'} | "
        f"zim={'ok' if exists else 'fehlt'} | "
        f"max_terms={int(_value(settings, 'offline_wiki_max_terms', 2) or 2)} | "
        f"chars={int(_value(settings, 'offline_wiki_max_chars', 1400) or 1400)}/"
        f"{int(_value(settings, 'offline_wiki_multi_max_chars', 700) or 700)} | "
        f"last={terms} -> {titles}"
    )


def command_wiki(settings: Any, args: list[str]) -> str:
    if not args or args[0].lower() == "status":
        return status_text(settings)

    raw = args[0].lower()
    data = _settings(settings)
    if raw in {"on", "off"}:
        data["offline_wiki_enabled"] = raw == "on"
        return f"Offline Wiki {'aktiviert' if data['offline_wiki_enabled'] else 'deaktiviert'}."
    if raw == "auto" and len(args) >= 2:
        data["offline_wiki_auto"] = args[1].lower() in {"on", "true", "1", "ja"}
        return f"Offline Wiki Auto-Lookup {'an' if data['offline_wiki_auto'] else 'aus'}."
    if raw == "debug" and len(args) >= 2:
        data["offline_wiki_debug"] = args[1].lower() in {"on", "true", "1", "ja"}
        return f"Offline Wiki Debug {'an' if data['offline_wiki_debug'] else 'aus'}."
    if raw == "path" and len(args) >= 2:
        data["offline_wiki_zim_path"] = os.path.abspath(os.path.expanduser(" ".join(args[1:]).strip()))
        reset_archive()
        return f"Offline-Wiki Pfad gesetzt: {data['offline_wiki_zim_path']}"
    if raw == "test" and len(args) >= 2:
        term = _clean_term(" ".join(args[1:]).strip())
        hit, ok = lookup(term, settings)
        if not ok or not hit:
            return SESSION.get("last_error") or f"Kein Treffer für {term}."
        return f"Offline-Wiki Treffer: {hit['title']}\nQuelle: {hit['source']}\n\n{hit['text'][:900]}"

    term = _clean_term(" ".join(args).strip())
    hit, ok = lookup(term, settings)
    if not ok or not hit:
        return SESSION.get("last_error") or f"Kein Treffer für {term}."
    return f"Offline-Wiki Treffer: {hit['title']}\nQuelle: {hit['source']}\n\n{hit['text'][:900]}"
