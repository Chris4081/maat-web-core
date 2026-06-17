from __future__ import annotations

import ast
import hashlib
import html
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import DATA_DIR, RuntimeSettings


DOCS_ROOT = DATA_DIR / "docs"
INDEX_FILE = DOCS_ROOT / "files.jsonl"
FEEDBACK_LOG_FILE = DOCS_ROOT / "feedback_logs.jsonl"
PENDING_FEEDBACK_FILE = DOCS_ROOT / "pending_feedback.json"
RUNS_ROOT = DOCS_ROOT / "_runs"

ALLOWED_EXTENSIONS = {
    ".md": "Markdown",
    ".txt": "Text",
    ".py": "Python",
    ".tex": "LaTeX",
    ".html": "HTML",
    ".htm": "HTML",
    ".json": "JSON",
    ".csv": "CSV",
    ".pdf": "PDF",
}

LANGUAGE_EXTENSIONS = {
    "markdown": ".md",
    "md": ".md",
    "text": ".txt",
    "txt": ".txt",
    "plain": ".txt",
    "python": ".py",
    "py": ".py",
    "latex": ".tex",
    "tex": ".tex",
    "html": ".html",
    "htm": ".html",
    "json": ".json",
    "csv": ".csv",
}

EXTENSION_DIRS = {
    ".md": "markdown",
    ".txt": "text",
    ".py": "python",
    ".tex": "latex",
    ".html": "html",
    ".json": "json",
    ".csv": "csv",
    ".pdf": "pdf",
}

FENCE_RE = re.compile(
    r"(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)\n(?P<content>.*?)(?:\n(?P=fence))",
    re.DOTALL,
)
BRACKET_BLOCK_RE = re.compile(
    r"\[(?:MAAT_FILE|DATEI|FILE)\s*:\s*(?P<name>[^\]\n]+)\]\s*\n?"
    r"(?P<content>.*?)\n?\[/(?:MAAT_FILE|DATEI|FILE)\]",
    re.IGNORECASE | re.DOTALL,
)
XML_BLOCK_RE = re.compile(
    r"<maat[-_ ]?file\b(?P<attrs>[^>]*)>(?P<content>.*?)</maat[-_ ]?file>",
    re.IGNORECASE | re.DOTALL,
)
RAW_TEX_DOCUMENT_RE = re.compile(r"(?P<content>\\documentclass\b.*?\\end\{document\})", re.DOTALL)
RAW_PYTHON_START_RE = re.compile(r"(?m)^(?:import\s+[A-Za-z_][\w.]*|from\s+[A-Za-z_][\w.]*\s+import\s+)")
ATTR_NAME_RE = re.compile(
    r"(?:filename|file|name)\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s>]+))",
    re.IGNORECASE,
)
FILENAME_TOKEN_RE = re.compile(
    r"(?<![\w./-])([A-Za-z0-9][A-Za-z0-9_. -]{0,90}\.(?:md|txt|py|tex|html?|json|csv))"
    r"(?=$|[\s`'\"\*\)\]\}>;,:!?]|\.(?=\s|$))",
    re.IGNORECASE,
)
RUN_COMMAND_FILENAME_RE = re.compile(
    r"(?:python3?|py|pygame)\s+([A-Za-z0-9][A-Za-z0-9_. -]{0,90}\.py)"
    r"(?=$|[\s`'\"\*\)\]\}>;,:!?]|\.(?=\s|$))",
    re.IGNORECASE,
)
PYTHON_UI_CODE_LABEL_RE = re.compile(
    r"(?im)^\s*(?:code\s*(?:[·:\-]\s*)?)?(?:python|py)\s*$"
)
INLINE_NAME_RE = re.compile(
    r"^\s*(?:#|//|%|;|<!--)?\s*(?:filename|dateiname|file|datei)\s*[:=]\s*"
    r"([^\n<>]+?\.(?:md|txt|py|tex|html?|json|csv))\s*(?:-->)?\s*$",
    re.IGNORECASE,
)
USEPACKAGE_LINE_RE = re.compile(
    r"^(?P<indent>\s*)\\usepackage(?:\[(?P<options>[^\]]*)\])?\{(?P<package>[A-Za-z0-9_.-]+)\}\s*(?P<comment>%.*)?$"
)
BUILDER_CONTEXT_BLOCK_RE = re.compile(
    r"\s*\[MAAT_FILE_BUILDER(?:_FEEDBACK)?\].*?\[/MAAT_FILE_BUILDER(?:_FEEDBACK)?\]\s*",
    re.IGNORECASE | re.DOTALL,
)
DOCS_CARD_BLOCK_RE = re.compile(
    r"\s*\[MAAT_DOCS_CARD\].*?\[/MAAT_DOCS_CARD\]\s*",
    re.IGNORECASE | re.DOTALL,
)
THINK_BLOCK_RE = re.compile(r"\s*<think\b[^>]*>.*?</think>\s*", re.IGNORECASE | re.DOTALL)
THINK_OPEN_RE = re.compile(r"\s*<think\b[^>]*>.*", re.IGNORECASE | re.DOTALL)
BRACKET_THINK_BLOCK_RE = re.compile(
    r"\s*\[(denken|thinking|gedanken)\].*?\[/\1\]\s*",
    re.IGNORECASE | re.DOTALL,
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
FINAL_ANSWER_LABEL_RE = re.compile(
    r"^\s*(?:\[(?:antwort|final|final answer|output)\]|(?:final output generation|final output|final answer|antwort|output)\s*:)\s*",
    re.IGNORECASE | re.MULTILINE,
)
FINAL_ANSWER_START_RE = re.compile(
    r"^\s*(?P<answer>gern geschehen[!,.]?|gern[!,.]?|gerne[!,.]?|sehr gern[!,.]?|kein problem[!,.]?|hallo\b|hi\b|hey\b|klar[!,.]?|alles klar[!,.]?|natürlich[!,.]?|ja[!,.]?|nein[!,.]?|gut[!,.]?|passt[!,.]?|fertig[!,.]?|hier\b|hier\s+(?:ist|kommt|die|der|das)\b|das\s+(?:ist|passt|geht|klingt)\b|ich\s+(?:habe|würde|sehe|denke)\b|die wohl bekannteste\b|die bekannteste\b|die formel\b|einstein\b)",
    re.IGNORECASE | re.MULTILINE,
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
BUILDER_UI_ARTIFACT_LINE_RE = re.compile(
    r"^\s*(?:"
    r"copy|vorlesen|denken anzeigen|"
    r"py download|py öffnen|py ausführen|"
    r"tex download|tex öffnen|pdf download|pdf öffnen|"
    r"terminal gestartet|python syntax-check fehlgeschlagen\.?|"
    r"📄\s*(?:datei(?: angelegt)?|docs? angelegt|[0-9]+\s+dateien angelegt).*|"
    r"(?:python|latex|tex|html|markdown|text|json|csv|pdf)\s*·\s*[^/]+/.*"
    r")\s*$",
    re.IGNORECASE,
)
EMPTY_BUILDER_ARTIFACT_FENCE_RE = re.compile(
    r"\n?```[^\n]*\n(?:(?:\s*(?:"
    r"copy|vorlesen|denken anzeigen|"
    r"py download|py öffnen|py ausführen|"
    r"tex download|tex öffnen|pdf download|pdf öffnen|"
    r"terminal gestartet|python syntax-check fehlgeschlagen\.?|"
    r"📄\s*(?:datei(?: angelegt)?|docs? angelegt|[0-9]+\s+dateien angelegt).*|"
    r"(?:python|latex|tex|html|markdown|text|json|csv|pdf)\s*·\s*[^/]+/.*"
    r")\s*\n)+)```\s*",
    re.IGNORECASE,
)
RAW_CODE_STOP_RE = re.compile(
    r"^\s*(?:"
    r"starte\s+mit\b|neu:|sag bescheid\b|ein konkreter anker\b|"
    r"📄\s*(?:datei|[0-9]+\s+dateien)|"
    r"py download|py öffnen|py ausführen|"
    r"code\s*(?:[·:\-]\s*)?(?:python|py)?\s*$|"
    r"copy\s*$"
    r")",
    re.IGNORECASE,
)


@dataclass
class FileBlock:
    filename: str
    content: str
    span: tuple[int, int]
    source: str


def _enabled(settings: RuntimeSettings) -> bool:
    return bool(getattr(settings, "file_builder_enabled", True))


def _ensure_dirs() -> None:
    DOCS_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in set(EXTENSION_DIRS.values()):
        (DOCS_ROOT / folder).mkdir(parents=True, exist_ok=True)


def _normalise_extension(ext: str) -> str:
    ext = (ext or "").lower()
    return ".html" if ext == ".htm" else ext


def _extension_from_language(info: str) -> str | None:
    token = (info or "").strip().split(maxsplit=1)
    if not token:
        return None
    return LANGUAGE_EXTENSIONS.get(token[0].lower().replace("language-", ""))


def _extension_from_content(content: str) -> str | None:
    text = (content or "").lstrip()
    lower = text[:2000].lower()
    if "\\documentclass" in lower or "\\begin{document}" in lower:
        return ".tex"
    if lower.startswith("<!doctype html") or re.search(r"<html\b", lower):
        return ".html"
    if re.match(r"^\s*(import|from)\s+\w+|^\s*def\s+\w+\(|^\s*class\s+\w+|\bprint\s*\(", text):
        return ".py"
    if text.startswith("# ") or text.startswith("## ") or "\n# " in text:
        return ".md"
    if text.startswith("{") or text.startswith("["):
        try:
            json.loads(text)
            return ".json"
        except Exception:
            pass
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    if first_line.count(",") >= 1 and len(text.splitlines()) >= 2:
        return ".csv"
    return None


def _clean_filename(name: str | None) -> str:
    raw = html.unescape(str(name or "")).strip().strip("\"'`")
    raw = raw.replace("\\", "/")
    raw = Path(raw).name
    raw = re.sub(r"[\x00-\x1f\x7f]", "", raw).strip().strip(".")
    return raw


def _safe_filename(name: str | None, fallback_ext: str = ".txt") -> str:
    fallback_ext = _normalise_extension(fallback_ext)
    if fallback_ext not in ALLOWED_EXTENSIONS:
        fallback_ext = ".txt"
    raw = _clean_filename(name) or f"maat_output{fallback_ext}"
    stem, ext = os.path.splitext(raw)
    ext = _normalise_extension(ext) or fallback_ext
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Dateiendung nicht erlaubt: {ext}")
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", stem.strip() or "maat_output")
    stem = re.sub(r"\s+", "_", stem).strip("._- ")[:80] or "maat_output"
    return f"{stem}{ext}"


def _extract_name_from_attrs(text: str) -> str | None:
    match = ATTR_NAME_RE.search(text or "")
    if not match:
        return None
    return next((group for group in match.groups() if group), None)


def _compact_filename_phrase(raw: str) -> str:
    raw = str(raw or "").strip()
    lower = raw.lower()
    if re.search(r"\b(?:datei|file|als|python|programm|script|skript|speichere|erstelle|programmiere|baue|mach|starte)\b", lower):
        compact_tail = re.search(
            r"([A-Za-z0-9][A-Za-z0-9_.-]{0,90}\.(?:md|txt|py|tex|html?|json|csv))$",
            raw,
            re.IGNORECASE,
        )
        if compact_tail:
            return compact_tail.group(1).strip()
    return raw


def _extract_filename_token(text: str) -> str | None:
    for match in FILENAME_TOKEN_RE.finditer(text or ""):
        return _compact_filename_phrase(match.group(1))
    return None


def _extract_nearby_filename(text: str, span: tuple[int, int], preferred_ext: str | None = None) -> str | None:
    preferred_ext = _normalise_extension(preferred_ext or "")
    start, end = span
    after = str(text or "")[end : min(len(str(text or "")), end + 900)]
    before = str(text or "")[max(0, start - 450) : start]
    windows = [after, before]
    if preferred_ext == ".py":
        for window in windows:
            match = RUN_COMMAND_FILENAME_RE.search(window)
            if match:
                return match.group(1).strip()
    for window in windows:
        for match in FILENAME_TOKEN_RE.finditer(window):
            name = _compact_filename_phrase(match.group(1))
            if not preferred_ext or _normalise_extension(Path(name).suffix) == preferred_ext:
                return name
    return None


def _python_capture_signal(
    text: str,
    span: tuple[int, int],
    user_input: str,
    wants_file: bool,
    requested_ext: str | None,
) -> bool:
    if wants_file and requested_ext == ".py":
        return True

    start, end = span
    full_text = str(text or "")
    before = full_text[max(0, start - 450) : start]
    after = full_text[end : min(len(full_text), end + 900)]
    if PYTHON_UI_CODE_LABEL_RE.search(before):
        return True
    if RUN_COMMAND_FILENAME_RE.search(before) or RUN_COMMAND_FILENAME_RE.search(after):
        return True

    lower = str(user_input or "").lower()
    return bool(
        ("python" in lower or ".py" in lower or "pygame" in lower)
        and any(word in lower for word in ("datei", "file", "code", "programm", "script", "skript", "spiel", "game"))
    )


def _python_code_score(content: str) -> int:
    text = content or ""
    score = 0
    if re.search(r"(?m)^\s*(?:import|from)\s+[A-Za-z_][\w.]*", text):
        score += 1
    if re.search(r"(?m)^\s*(?:class|def)\s+[A-Za-z_]\w*", text):
        score += 2
    if re.search(r"(?m)^\s*if\s+__name__\s*==\s*['\"]__main__['\"]", text):
        score += 2
    if re.search(r"\b(?:pygame\.|print\s*\(|sys\.exit\s*\(|while\s+True\s*:|for\s+\w+.+?:)", text):
        score += 1
    if len([line for line in text.splitlines() if line.strip()]) >= 6:
        score += 1
    return score


def _find_raw_python_end(text: str, start: int) -> int | None:
    lines = str(text or "")[start:].splitlines(keepends=True)
    prefix = ""
    last_valid_len = 0
    max_lines = min(len(lines), 1400)
    for line in lines[:max_lines]:
        prefix += line
        candidate = prefix.rstrip()
        if not candidate:
            continue
        if len(candidate.encode("utf-8")) > 2_000_000:
            break
        try:
            ast.parse(candidate + "\n")
        except SyntaxError:
            continue
        if _python_code_score(candidate) >= 3:
            last_valid_len = len(candidate)
    return start + last_valid_len if last_valid_len else None


def _find_raw_python_end_fallback(text: str, start: int) -> int | None:
    lines = str(text or "")[start:].splitlines(keepends=True)
    collected: list[str] = []
    blank_run = 0
    for line in lines[:1400]:
        if collected and RAW_CODE_STOP_RE.match(line):
            break
        if not line.strip():
            blank_run += 1
            collected.append(line)
            continue
        blank_run = 0
        collected.append(line)
        if len("".join(collected).encode("utf-8")) > 2_000_000:
            break
    content = "".join(collected).rstrip()
    if _python_code_score(content) < 3:
        return None
    code_lines = [line for line in content.splitlines() if line.strip()]
    if len(code_lines) < 6:
        return None
    return start + len(content)


def _expand_python_ui_span_start(text: str, code_start: int) -> int:
    window_start = max(0, code_start - 700)
    prefix = str(text or "")[window_start:code_start]
    artifact_fence = re.search(
        r"(?is)(^|\n)(?P<label>\s*(?:`{3,}|~{3,})\s*(?:python|py)[^\n]*\n"
        r"(?:(?:\s*(?:copy|vorlesen|denken anzeigen|py download|py öffnen|py ausführen|"
        r"terminal gestartet|python syntax-check fehlgeschlagen\.?|"
        r"📄\s*(?:datei(?: angelegt)?|docs? angelegt|[0-9]+\s+dateien angelegt).*|"
        r"(?:python|latex|tex|html|markdown|text|json|csv|pdf)\s*·\s*[^/]+/.*)\s*\n)+)"
        r"(?:`{3,}|~{3,})\s*)$",
        prefix,
    )
    if artifact_fence:
        return window_start + artifact_fence.start("label")

    match = re.search(
        r"(?im)(^|\n)(?P<label>\s*(?:(?:`{3,}|~{3,})\s*(?:python|py)[^\n]*|(?:code\s*(?:[·:\-]\s*)?)?(?:python|py))\s*\n(?:\s*copy\s*\n)?)\s*$",
        prefix,
    )
    if not match:
        return code_start
    return window_start + match.start("label")


def _strip_builder_artifact_lines(content: str) -> str:
    lines = str(content or "").splitlines()
    cleaned = [line for line in lines if not BUILDER_UI_ARTIFACT_LINE_RE.match(line)]
    return "\n".join(cleaned).strip("\n")


def _strip_empty_builder_artifact_fences(text: str) -> str:
    return EMPTY_BUILDER_ARTIFACT_FENCE_RE.sub("\n\n", str(text or ""))


def _find_internal_final_answer_start(text: str) -> int:
    value = str(text or "")
    label_match = FINAL_ANSWER_LABEL_RE.search(value)
    if label_match and label_match.end() < len(value):
        return label_match.end()
    for match in FINAL_ANSWER_START_RE.finditer(value):
        if match.start("answer") > 24:
            return match.start("answer")
    return -1


def _strip_inline_filename(content: str) -> tuple[str, str | None]:
    lines = (content or "").splitlines()
    for index, line in enumerate(lines[:3]):
        match = INLINE_NAME_RE.match(line)
        if match:
            del lines[index]
            return "\n".join(lines).strip("\n"), match.group(1)
    return content, None


def _infer_requested_file(user_input: str) -> tuple[bool, str | None, str | None]:
    text = user_input or ""
    lower = text.lower()
    explicit_name = _extract_filename_token(text)
    if explicit_name:
        _, ext = os.path.splitext(explicit_name)
        ext = _normalise_extension(ext)
        return True, explicit_name, ext if ext in ALLOWED_EXTENSIONS else None

    mentions_action = any(
        word in lower
        for word in (
            "datei",
            "file",
            "download",
            "anhang",
            "speichern",
            "export",
            "code",
            "programm",
            "program",
            "script",
            "skript",
            "tool",
            "app",
            "spiel",
            "game",
            "erstelle",
            "erstell",
            "schreib",
            "baue",
            "programmiere",
            "latex",
            "html",
            "json",
            "csv",
        )
    )

    ext = None
    if re.search(r"\.md\b|markdown", lower):
        ext = ".md"
    elif re.search(r"\.txt\b|textdatei|plain text", lower):
        ext = ".txt"
    elif re.search(r"\.py\b|python|pygame|\bcode\b|programm|script|skript|tool|app|spiel|game", lower):
        ext = ".py"
    elif re.search(r"\.tex\b|latex|\btex\b", lower):
        ext = ".tex"
    elif re.search(r"\.html?\b|html", lower):
        ext = ".html"
    elif re.search(r"\.json\b|json", lower):
        ext = ".json"
    elif re.search(r"\.csv\b|csv", lower):
        ext = ".csv"

    wants = bool(mentions_action and ext)
    return wants, (f"maat_output{ext}" if ext else None), ext


def build_file_builder_prompt(settings: RuntimeSettings, user_input: str) -> tuple[str, dict[str, Any]]:
    wants_file, requested_name, requested_ext = _infer_requested_file(user_input)
    info = {
        "enabled": _enabled(settings),
        "wants_file": wants_file,
        "requested_name": requested_name,
        "requested_ext": requested_ext,
    }
    if not _enabled(settings) or not bool(getattr(settings, "file_builder_inject_instructions", True)) or not wants_file:
        return "", info

    filename_hint = requested_name or f"passender_name{requested_ext or '.txt'}"
    tex_rule = ""
    if requested_ext == ".tex":
        tex_rule = (
            "Fuer .tex-Dateien muss der Block ein vollstaendiges, eigenstaendig kompilierbares "
            "LaTeX-Dokument enthalten: \\documentclass, \\begin{document}, \\end{document}.\n"
        )
    return (
        "\n\n[MAAT_FILE_BUILDER]\n"
        "Nutze diesen Block nur intern. Wenn der Nutzer eine Datei, Code, LaTeX, HTML, JSON, CSV oder einen Download moechte, "
        "gib den vollstaendigen Dateiinhalt in genau diesem Format aus:\n"
        f"[MAAT_FILE: {filename_hint}]\n"
        "...vollstaendiger Dateiinhalt ohne Erklaertext innerhalb des Blocks...\n"
        "[/MAAT_FILE]\n"
        "Du darfst vor oder nach dem Block kurz erklaeren. Gib niemals nur save:(...) aus, wenn eine Datei gewuenscht ist.\n"
        f"{tex_rule}"
        "Erlaubte Endungen: .md, .txt, .py, .tex, .html, .json, .csv.\n"
        "[/MAAT_FILE_BUILDER]",
        info,
    )


def _tail_text(value: str, max_chars: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return "[...Log gekuerzt...]\n" + text[-max_chars:].lstrip()


def _append_feedback_log(record: dict[str, Any]) -> None:
    _ensure_dirs()
    with FEEDBACK_LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    PENDING_FEEDBACK_FILE.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def _store_feedback(kind: str, path: Path, output: str, summary: str) -> dict[str, Any]:
    record = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "kind": kind,
        "filename": path.name,
        "path": str(path.resolve()),
        "summary": summary,
        "output": output,
    }
    _append_feedback_log(record)
    return record


def build_file_builder_feedback_prompt(settings: RuntimeSettings) -> tuple[str, dict[str, Any]]:
    info: dict[str, Any] = {"pending": False}
    if not _enabled(settings) or not bool(getattr(settings, "file_builder_inject_feedback", True)):
        return "", info
    _collect_finished_terminal_runs()
    if not PENDING_FEEDBACK_FILE.exists():
        return "", info
    try:
        record = json.loads(PENDING_FEEDBACK_FILE.read_text(encoding="utf-8"))
    except Exception:
        PENDING_FEEDBACK_FILE.unlink(missing_ok=True)
        return "", info

    PENDING_FEEDBACK_FILE.unlink(missing_ok=True)
    max_chars = max(500, int(getattr(settings, "file_builder_feedback_chars", 6000) or 6000))
    output = _tail_text(record.get("output") or "", max_chars)
    kind = record.get("kind") or "file_check"
    filename = record.get("filename") or "(unbekannt)"
    summary = record.get("summary") or "Der letzte Datei-Check hat einen Fehler gefunden."
    info = {
        "pending": True,
        "kind": kind,
        "filename": filename,
        "summary": summary,
    }
    return (
        "\n\n[MAAT_FILE_BUILDER_FEEDBACK]\n"
        "Nutze diesen Block nur intern. Der zuletzt erzeugte Dateiinhalt hatte ein Problem. "
        "Wenn der Nutzer nachfragt oder weiter am Code/LaTeX arbeitet, erklaere den Fehler kurz und liefere eine korrigierte Datei.\n"
        f"Typ: {kind}\n"
        f"Datei: {filename}\n"
        f"Zusammenfassung: {summary}\n"
        "Log:\n"
        f"{output}\n"
        "[/MAAT_FILE_BUILDER_FEEDBACK]",
        info,
    )


def strip_file_builder_tags(text: str) -> str:
    return BUILDER_CONTEXT_BLOCK_RE.sub("\n\n", str(text or "")).strip()


def strip_file_builder_chat_cards(text: str) -> str:
    return DOCS_CARD_BLOCK_RE.sub("\n\n", str(text or "")).strip()


def _docs_card_block(records: list[dict[str, Any]], errors: list[str]) -> str:
    if not records and not errors:
        return ""
    payload = {
        "records": records,
        "errors": errors,
    }
    return "\n\n[MAAT_DOCS_CARD]\n" + json.dumps(payload, ensure_ascii=False) + "\n[/MAAT_DOCS_CARD]"


def _strip_thinking_blocks_for_builder(text: str) -> tuple[str, str]:
    """Return hidden thinking and visible answer text for file extraction.

    The builder must never create files from model reasoning.  We keep the
    hidden part so the chat can still render thinking when that mode is on.
    """
    value = str(text or "")
    hidden_parts: list[str] = []

    def remove_block(pattern: re.Pattern[str], current: str) -> str:
        def repl(match: re.Match[str]) -> str:
            hidden_parts.append(match.group(0).strip())
            return "\n\n"

        return pattern.sub(repl, current)

    visible = remove_block(THINK_BLOCK_RE, value)
    visible = remove_block(BRACKET_THINK_BLOCK_RE, visible)

    open_match = THINK_OPEN_RE.search(visible)
    if open_match:
        hidden_parts.append(visible[open_match.start() :].strip())
        visible = visible[: open_match.start()]

    if FREE_THINKING_START_RE.match(visible):
        answer_start = _find_internal_final_answer_start(visible)
        if answer_start >= 0:
            hidden_parts.append(visible[:answer_start].strip())
            visible = visible[answer_start:]
        else:
            hidden_parts.append(visible.strip())
            visible = ""
    else:
        answer_start = _find_internal_final_answer_start(visible)
        if answer_start > 0 and INTERNAL_THINKING_HINT_RE.search(visible[:answer_start]):
            hidden_parts.append(visible[:answer_start].strip())
            visible = visible[answer_start:]

    hidden = "\n\n".join(part for part in hidden_parts if part)
    visible = re.sub(r"\n{3,}", "\n\n", visible).strip()
    return hidden, visible


def _join_thinking_and_visible(thinking: str, visible: str) -> str:
    thinking = str(thinking or "").strip()
    visible = str(visible or "").strip()
    if thinking and visible:
        return f"{thinking}\n\n{visible}"
    return thinking or visible


def _overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(max(start, other_start) < min(end, other_end) for other_start, other_end in spans)


def _is_diagnostic_block(content: str) -> bool:
    text = (content or "").strip()
    if len(text) > 480:
        return False
    has_scores = re.search(r"\bH\s*=\s*\d+(?:\.\d+)?\b.*\bB\s*=\s*\d+(?:\.\d+)?\b.*\bR\s*=\s*\d+(?:\.\d+)?\b", text, re.DOTALL)
    return bool(has_scores and re.search(r"\bStability\b|\bMaat Value\b|\bFokusfelder\b", text, re.IGNORECASE))


def _extract_blocks(text: str, user_input: str, settings: RuntimeSettings) -> list[FileBlock]:
    blocks: list[FileBlock] = []
    used: list[tuple[int, int]] = []
    wants_file, requested_name, requested_ext = _infer_requested_file(user_input)

    for match in XML_BLOCK_RE.finditer(text):
        filename = _extract_name_from_attrs(match.group("attrs") or "") or requested_name or "maat_output.txt"
        content = html.unescape(match.group("content").strip("\n"))
        content, inline_name = _strip_inline_filename(content)
        blocks.append(FileBlock(inline_name or filename, content, match.span(), "xml"))
        used.append(match.span())

    for match in BRACKET_BLOCK_RE.finditer(text):
        if _overlaps(match.span(), used):
            continue
        content = html.unescape(match.group("content").strip("\n"))
        content, inline_name = _strip_inline_filename(content)
        blocks.append(FileBlock(inline_name or match.group("name").strip(), content, match.span(), "bracket"))
        used.append(match.span())

    for match in FENCE_RE.finditer(text):
        if _overlaps(match.span(), used):
            continue
        info = (match.group("info") or "").strip()
        content = html.unescape(match.group("content").strip("\n"))
        if _is_diagnostic_block(content):
            continue
        content = _strip_builder_artifact_lines(content)
        if not content.strip():
            continue
        content, inline_name = _strip_inline_filename(content)
        ext_from_lang = _extension_from_language(info)
        ext_from_content = _extension_from_content(content)
        target_ext = ext_from_lang or ext_from_content or requested_ext
        nearby_name = _extract_nearby_filename(text, match.span(), target_ext)
        filename = _extract_name_from_attrs(info) or _extract_filename_token(info) or inline_name or nearby_name
        if not filename and wants_file and bool(getattr(settings, "file_builder_auto_capture_fences", True)):
            if target_ext:
                filename = requested_name if requested_name and requested_name.endswith(target_ext) else f"maat_output{target_ext}"
        if not filename:
            continue
        if not os.path.splitext(filename)[1]:
            filename = f"{filename}{ext_from_lang or ext_from_content or requested_ext or '.txt'}"
        blocks.append(FileBlock(filename, content, match.span(), "fence"))
        used.append(match.span())

    if wants_file:
        for match in RAW_TEX_DOCUMENT_RE.finditer(text):
            if _overlaps(match.span(), used):
                continue
            filename = requested_name if requested_name and requested_name.endswith(".tex") else "maat_output.tex"
            blocks.append(FileBlock(filename, match.group("content").strip("\n"), match.span(), "raw_tex"))
            used.append(match.span())

    for match in RAW_PYTHON_START_RE.finditer(text):
        code_start = match.start()
        if _overlaps((code_start, code_start + 1), used):
            continue
        code_end = _find_raw_python_end(text, code_start) or _find_raw_python_end_fallback(text, code_start)
        if not code_end:
            continue
        display_start = _expand_python_ui_span_start(text, code_start)
        display_span = (display_start, code_end)
        code_span = (code_start, code_end)
        if _overlaps(display_span, used):
            continue
        if not _python_capture_signal(text, code_span, user_input, wants_file, requested_ext):
            continue
        filename = (
            requested_name
            if requested_name and _normalise_extension(Path(requested_name).suffix) == ".py"
            else _extract_nearby_filename(text, code_span, ".py") or "maat_output.py"
        )
        content = _strip_builder_artifact_lines(html.unescape(str(text or "")[code_start:code_end].strip("\n")))
        if not content.strip():
            continue
        blocks.append(FileBlock(filename, content, display_span, "raw_python"))
        used.append(display_span)

    return sorted(blocks, key=lambda item: item.span[0])


def _record_id(path: Path, created_at: str) -> str:
    return hashlib.sha1(f"{path.resolve()}:{created_at}".encode("utf-8")).hexdigest()[:16]


def _append_index(record: dict[str, Any]) -> None:
    _ensure_dirs()
    with INDEX_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_index(limit: int = 80) -> list[dict[str, Any]]:
    if not INDEX_FILE.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = INDEX_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        path = Path(record.get("path") or "")
        if path.exists():
            records.append(record)
        if len(records) >= limit:
            break
    return records


def _read_index_all() -> list[dict[str, Any]]:
    if not INDEX_FILE.exists():
        return []
    try:
        lines = INDEX_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    records: list[dict[str, Any]] = []
    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        path = Path(record.get("path") or "")
        if path.exists():
            records.append(record)
    return records


def _write_index(records: list[dict[str, Any]]) -> None:
    _ensure_dirs()
    if not records:
        INDEX_FILE.unlink(missing_ok=True)
        return
    temp_path = INDEX_FILE.with_suffix(".jsonl.tmp")
    temp_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(INDEX_FILE)


def _is_managed_doc_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
        root = DOCS_ROOT.resolve()
    except OSError:
        return False
    return resolved.exists() and root in resolved.parents


def _target_path(filename: str) -> Path:
    safe = _safe_filename(filename)
    ext = _normalise_extension(Path(safe).suffix)
    folder = EXTENSION_DIRS.get(ext, "text")
    target_dir = DOCS_ROOT / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / safe
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return target_dir / f"{stem}_{stamp}{suffix}"


def _repair_latex_package_option_clashes(content: str) -> str:
    lines = str(content or "").splitlines()
    groups: dict[str, list[tuple[int, re.Match[str]]]] = {}
    for index, line in enumerate(lines):
        match = USEPACKAGE_LINE_RE.match(line)
        if not match:
            continue
        package = (match.group("package") or "").strip().lower()
        groups.setdefault(package, []).append((index, match))

    replacements: dict[int, str] = {}
    skip: set[int] = set()
    for package, matches in groups.items():
        if len(matches) <= 1:
            continue

        def score(item: tuple[int, re.Match[str]]) -> tuple[int, int]:
            _index, match = item
            options = (match.group("options") or "").strip()
            if package == "tcolorbox" and "most" in {part.strip().lower() for part in options.split(",")}:
                return (3, len(options))
            return (1 if options else 0, len(options))

        first_index = matches[0][0]
        chosen_index, chosen_match = max(matches, key=score)
        chosen_line = lines[chosen_index]
        replacements[first_index] = chosen_line
        for index, _match in matches:
            if index != first_index:
                skip.add(index)

    if not replacements and not skip:
        return str(content or "")

    repaired = []
    for index, line in enumerate(lines):
        if index in skip:
            continue
        repaired.append(replacements.get(index, line))
    return "\n".join(repaired) + ("\n" if str(content or "").endswith("\n") else "")


def _repair_latex_unclosed_lists(content: str) -> str:
    text = str(content or "")
    if "\\end{document}" not in text:
        return text
    stack: list[str] = []
    for match in re.finditer(r"\\(begin|end)\{(itemize|enumerate|description)\}", text):
        kind, env = match.group(1), match.group(2)
        if kind == "begin":
            stack.append(env)
        elif stack and stack[-1] == env:
            stack.pop()
        elif env in stack:
            stack.remove(env)
    if not stack:
        return text
    closing = "\n" + "\n".join(f"\\end{{{env}}}" for env in reversed(stack)) + "\n"
    return text.replace("\\end{document}", f"{closing}\\end{{document}}", 1)


def _repair_latex_empty_linebreaks(content: str) -> str:
    return re.sub(r"(?m)^(\s*)\\\\\s*$", r"\1\\vspace{0.35em}", str(content or ""))


def _repair_latex_common_issues(content: str) -> str:
    repaired = _repair_latex_package_option_clashes(content)
    repaired = _repair_latex_unclosed_lists(repaired)
    repaired = _repair_latex_empty_linebreaks(repaired)
    return repaired


def _save_content(filename: str, content: str, source: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_dirs()
    safe = _safe_filename(filename, _extension_from_content(content or "") or ".txt")
    if _normalise_extension(Path(safe).suffix) == ".tex":
        content = _repair_latex_common_issues(content or "")
    path = _target_path(safe)
    path.write_text(content or "", encoding="utf-8")
    record = _record_for_path(path, source, metadata)
    _append_index(record)
    return record


def _record_for_path(path: Path, source: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    created_at = time.strftime("%Y-%m-%dT%H:%M:%S")
    record = {
        "id": _record_id(path, created_at),
        "created_at": created_at,
        "filename": path.name,
        "path": str(path.resolve()),
        "relative_path": str(path.resolve().relative_to(DOCS_ROOT.resolve())),
        "extension": _normalise_extension(path.suffix),
        "bytes": path.stat().st_size,
        "source": source,
    }
    if metadata:
        record.update(metadata)
    return record


def _format_process_log(command: list[str], completed: subprocess.CompletedProcess[str]) -> str:
    return (
        f"$ {' '.join(command)}\n"
        f"exit code: {completed.returncode}\n\n"
        f"STDOUT:\n{(completed.stdout or '').strip() or '(leer)'}\n\n"
        f"STDERR:\n{(completed.stderr or '').strip() or '(leer)'}"
    )


def _summarize_tex_compile_log(output: str, cap: int = 1800) -> str:
    lines = str(output or "").splitlines()
    if not lines:
        return ""
    patterns = (
        r"^!",
        r"^l\.\d+",
        r"fatal error",
        r"emergency stop",
        r"undefined control sequence",
        r"missing",
        r"runaway argument",
        r"no output pdf",
        r"option clash",
    )
    interesting_index = None
    for index, line in enumerate(lines):
        lower = line.lower()
        if any(re.search(pattern, line, re.IGNORECASE) or re.search(pattern, lower, re.IGNORECASE) for pattern in patterns):
            interesting_index = index
            break
    if interesting_index is None:
        excerpt = lines[-30:]
    else:
        excerpt = lines[max(0, interesting_index - 8) : min(len(lines), interesting_index + 18)]
    summary = "\n".join(excerpt).strip()
    cap = max(500, min(int(cap or 1800), 2400))
    if len(summary) > cap:
        summary = summary[:cap].rstrip() + "\n[...pdflatex-Auszug gekürzt...]"
    return summary


def _tex_document_problem(tex_path: Path) -> str | None:
    try:
        content = tex_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"TeX-Datei konnte nicht gelesen werden: {exc}"
    stripped = content.lstrip()
    if not stripped:
        return "TeX-Datei ist leer."
    required = [
        ("\\documentclass", "fehlendes \\documentclass"),
        ("\\begin{document}", "fehlendes \\begin{document}"),
        ("\\end{document}", "fehlendes \\end{document}"),
    ]
    missing = [message for marker, message in required if marker not in content]
    if not missing:
        return None
    first_line = stripped.splitlines()[0][:140]
    return (
        "TeX-Datei ist nur ein Fragment und kein vollständiges LaTeX-Dokument "
        f"({', '.join(missing)}). Erste Zeile: {first_line}"
    )


def _terminal_meta_consumed_path(meta_path: Path) -> Path:
    return meta_path.with_name(meta_path.name + ".consumed")


def _collect_finished_terminal_runs() -> None:
    if not RUNS_ROOT.exists():
        return

    for meta_path in sorted(RUNS_ROOT.glob("*.meta.json")):
        consumed_path = _terminal_meta_consumed_path(meta_path)
        if consumed_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        status_path = Path(meta.get("status_path") or "")
        if not status_path.exists():
            continue

        try:
            status_lines = status_path.read_text(encoding="utf-8", errors="replace").splitlines()
            returncode = int(status_lines[0].strip()) if status_lines else 1
        except Exception:
            returncode = 1

        stdout_path = Path(meta.get("stdout_path") or "")
        stderr_path = Path(meta.get("stderr_path") or "")
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
        output = (
            f"$ {meta.get('shown', '')}\n"
            f"exit code: {returncode}\n\n"
            f"STDOUT:\n{stdout.strip() or '(leer)'}\n\n"
            f"STDERR:\n{stderr.strip() or '(leer)'}"
        )
        has_traceback = "Traceback (most recent call last)" in stdout or "Traceback (most recent call last)" in stderr
        if returncode != 0 or has_traceback:
            summary = f"Python-Terminal-Ausführung fehlgeschlagen (exit code {returncode})."
            _store_feedback("python_run", Path(meta.get("path") or "python.py"), output, summary)

        try:
            consumed_path.write_text(time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")
        except OSError:
            pass


def _write_python_terminal_runner(py_path: Path, args: list[str]) -> tuple[Path, Path, str]:
    _ensure_dirs()
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_id = f"{stamp}-{hashlib.sha1(f'{py_path}:{time.time()}'.encode('utf-8')).hexdigest()[:8]}"
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", py_path.stem)[:60] or "python"
    runner_path = RUNS_ROOT / f"{safe_stem}_{run_id}.command"
    stdout_path = RUNS_ROOT / f"{safe_stem}_{run_id}.stdout.log"
    stderr_path = RUNS_ROOT / f"{safe_stem}_{run_id}.stderr.log"
    status_path = RUNS_ROOT / f"{safe_stem}_{run_id}.status"
    meta_path = RUNS_ROOT / f"{safe_stem}_{run_id}.meta.json"
    shown = f"cd {shlex.quote(str(py_path.parent))} && {shlex.quote(sys.executable)} {shlex.quote(py_path.name)}"
    if args:
        shown += " " + " ".join(shlex.quote(arg) for arg in args)
    script_command = " ".join(shlex.quote(part) for part in [sys.executable, str(py_path.resolve()), *args])
    script = "\n".join(
        [
            "#!/bin/bash",
            "set +e",
            "export PYTHONUNBUFFERED=1",
            f"cd {shlex.quote(str(py_path.parent))}",
            f"echo {shlex.quote('$ ' + shown)}",
            f"{script_command} > >(tee -a {shlex.quote(str(stdout_path))}) 2> >(tee -a {shlex.quote(str(stderr_path))} >&2)",
            "code=$?",
            f"{{ echo \"$code\"; date '+%Y-%m-%dT%H:%M:%S%z'; }} > {shlex.quote(str(status_path))}",
            'echo ""',
            'echo "MAAT Docs: exit code $code"',
            'if [ "$code" -ne 0 ]; then',
            '  echo "Fehler erkannt. Der Terminal-Log wird beim naechsten Prompt an MAAT-KI gegeben."',
            "else",
            '  echo "Programm beendet ohne Fehler. Kein Fehlerlog wird injiziert."',
            "fi",
            'echo "Terminal bleibt offen. Schliessen mit: exit"',
            "exec /bin/bash -l",
        ]
    )
    runner_path.write_text(script + "\n", encoding="utf-8")
    runner_path.chmod(0o700)
    meta_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "path": str(py_path.resolve()),
                "shown": shown,
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "status_path": str(status_path),
                "wrapper_path": str(runner_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return runner_path, stdout_path, shown


def _open_python_in_terminal(py_path: Path, args: list[str]) -> dict[str, Any]:
    runner_path, log_path, shown = _write_python_terminal_runner(py_path, args)

    if sys.platform == "darwin" and shutil.which("open"):
        command = ["open", "-a", "Terminal", str(runner_path)]
    elif shutil.which("x-terminal-emulator"):
        command = ["x-terminal-emulator", "-e", str(runner_path)]
    elif shutil.which("gnome-terminal"):
        command = ["gnome-terminal", "--", str(runner_path)]
    elif shutil.which("konsole"):
        command = ["konsole", "-e", str(runner_path)]
    else:
        return {
            "ok": False,
            "error": "Kein Terminal-Starter gefunden.",
            "runner_path": str(runner_path),
            "log_path": str(log_path),
            "command": shown,
        }

    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "error": f"Terminal konnte nicht gestartet werden: {exc}",
            "runner_path": str(runner_path),
            "log_path": str(log_path),
            "command": shown,
        }

    if completed.returncode != 0:
        return {
            "ok": False,
            "error": (completed.stderr or completed.stdout or "Terminal konnte nicht gestartet werden.").strip(),
            "runner_path": str(runner_path),
            "log_path": str(log_path),
            "command": shown,
        }

    return {
        "ok": True,
        "terminal_started": True,
        "runner_path": str(runner_path),
        "log_path": str(log_path),
        "command": shown,
    }


def _compile_tex_to_pdf(settings: RuntimeSettings, tex_path: Path, metadata: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, str | None]:
    if not bool(getattr(settings, "file_builder_compile_tex_pdf", True)):
        return None, None
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        message = "pdflatex nicht gefunden. PDF wurde nicht erzeugt."
        _store_feedback("tex_compile", tex_path, message, message)
        return None, message

    document_problem = _tex_document_problem(tex_path)
    if document_problem:
        output = (
            "$ pdflatex wurde nicht gestartet.\n\n"
            f"{document_problem}\n\n"
            "Korrektur: Gib beim nächsten Versuch die komplette .tex-Datei aus, inklusive "
            "\\documentclass, Präambel, \\begin{document} und \\end{document}."
        )
        _store_feedback("tex_compile", tex_path, output, document_problem)
        return None, f"PDF nicht kompiliert: {document_problem}"

    build_dir = DOCS_ROOT / "_build" / tex_path.stem
    build_dir.mkdir(parents=True, exist_ok=True)
    timeout = max(5, int(getattr(settings, "file_builder_tex_timeout", 45) or 45))
    command = [
        pdflatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-no-shell-escape",
        "-output-directory",
        str(build_dir),
        str(tex_path),
    ]
    try:
        completed = None
        for _pass in range(2):
            completed = subprocess.run(
                command,
                cwd=str(tex_path.parent),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            if completed.returncode != 0:
                break
    except subprocess.TimeoutExpired as exc:
        output = f"$ {' '.join(command)}\nTimeout nach {timeout}s.\n\n{exc.stdout or ''}\n{exc.stderr or ''}"
        summary = f"LaTeX/PDF-Build Timeout nach {timeout}s."
        _store_feedback("tex_compile", tex_path, output, summary)
        return None, summary

    if completed is None:
        summary = "LaTeX/PDF-Build lieferte kein Ergebnis."
        _store_feedback("tex_compile", tex_path, summary, summary)
        return None, summary

    log = _format_process_log(command, completed)
    pdf_source = build_dir / f"{tex_path.stem}.pdf"
    if completed.returncode != 0 or not pdf_source.exists():
        excerpt = _summarize_tex_compile_log(log)
        summary = "LaTeX/PDF-Build fehlgeschlagen."
        if excerpt:
            summary = f"{summary}\n{excerpt}"
        _store_feedback("tex_compile", tex_path, log, summary)
        return None, summary

    pdf_target = _target_path(f"{tex_path.stem}.pdf")
    shutil.copy2(pdf_source, pdf_target)
    record = _record_for_path(
        pdf_target,
        "tex_pdf",
        {
            **(metadata or {}),
            "source_tex": str(tex_path.resolve()),
        },
    )
    _append_index(record)
    return record, None


def _check_python_syntax(settings: RuntimeSettings, py_path: Path) -> str | None:
    if not bool(getattr(settings, "file_builder_python_syntax_check", True)):
        return None
    timeout = max(1, int(getattr(settings, "file_builder_python_timeout", 8) or 8))
    command = [sys.executable, "-m", "py_compile", str(py_path)]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        output = f"$ {' '.join(command)}\nTimeout nach {timeout}s.\n\n{exc.stdout or ''}\n{exc.stderr or ''}"
        summary = f"Python Syntax-Check Timeout nach {timeout}s."
        _store_feedback("python_syntax", py_path, output, summary)
        return summary
    if completed.returncode != 0:
        log = _format_process_log(command, completed)
        summary = "Python Syntax-Check fehlgeschlagen."
        _store_feedback("python_syntax", py_path, log, summary)
        return summary
    return None


def run_python_doc(settings: RuntimeSettings, payload: dict[str, Any]) -> dict[str, Any]:
    if not _enabled(settings):
        return {"ok": False, "error": "MAAT Docs/File Builder ist deaktiviert.", **file_builder_state(settings)}
    if not bool(getattr(settings, "file_builder_python_run_enabled", True)):
        return {"ok": False, "error": "Python-Ausführung ist deaktiviert.", **file_builder_state(settings)}

    doc_id = str(payload.get("id") or payload.get("doc_id") or "")
    path = doc_path_by_id(doc_id)
    if path is None:
        return {"ok": False, "error": "Datei nicht gefunden.", **file_builder_state(settings)}
    if _normalise_extension(path.suffix) != ".py":
        return {"ok": False, "error": "Nur .py-Dateien können ausgeführt werden.", **file_builder_state(settings, selected=doc_id)}

    raw_args = str(payload.get("args") or "").strip()
    try:
        args = shlex.split(raw_args)
    except ValueError as exc:
        return {"ok": False, "error": f"Argumente konnten nicht gelesen werden: {exc}", **file_builder_state(settings, selected=doc_id)}

    prefer_terminal = payload.get("terminal")
    if prefer_terminal is None:
        prefer_terminal = getattr(settings, "file_builder_python_run_in_terminal", True)
    if bool(prefer_terminal):
        terminal_result = _open_python_in_terminal(path, args)
        if terminal_result.get("ok"):
            return {
                "ok": True,
                "returncode": None,
                "terminal_started": True,
                "output": (
                    "Terminal gestartet.\n\n"
                    f"$ {terminal_result.get('command')}\n\n"
                    f"Runner: {terminal_result.get('runner_path')}\n"
                    f"Log: {terminal_result.get('log_path')}"
                ),
                **terminal_result,
                **file_builder_state(settings, selected=doc_id),
            }
        terminal_error = terminal_result.get("error") or "Terminal konnte nicht gestartet werden."
    else:
        terminal_error = ""

    timeout = max(1, int(getattr(settings, "file_builder_python_timeout", 8) or 8))
    command = [sys.executable, str(path), *args]
    try:
        completed = subprocess.run(
            command,
            cwd=str(path.parent),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = _format_process_log(command, completed)
        ok = completed.returncode == 0
        feedback = None
        if not ok or "Traceback (most recent call last)" in output:
            summary = f"Python-Ausführung fehlgeschlagen (exit code {completed.returncode})."
            feedback = _store_feedback("python_run", path, output, summary)
            ok = False
        return {
            "ok": ok,
            "returncode": completed.returncode,
            "output": f"Terminal-Fallback: {terminal_error}\n\n{output}" if terminal_error else output,
            "feedback": feedback,
            **file_builder_state(settings, selected=doc_id),
        }
    except subprocess.TimeoutExpired as exc:
        output = f"$ {' '.join(command)}\nTimeout nach {timeout}s.\n\nSTDOUT:\n{exc.stdout or '(leer)'}\n\nSTDERR:\n{exc.stderr or '(leer)'}"
        summary = f"Python-Ausführung Timeout nach {timeout}s."
        feedback = _store_feedback("python_run", path, output, summary)
        return {
            "ok": False,
            "returncode": None,
            "output": output,
            "feedback": feedback,
            "error": summary,
            **file_builder_state(settings, selected=doc_id),
        }


def _save_content_bundle(
    settings: RuntimeSettings,
    filename: str,
    content: str,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    record = _save_content(filename, content, source, metadata)
    records = [record]
    errors: list[str] = []
    path = Path(record["path"])
    ext = _normalise_extension(path.suffix)
    if ext == ".tex":
        pdf_record, error = _compile_tex_to_pdf(settings, path, metadata)
        if pdf_record:
            records.append(pdf_record)
        if error:
            errors.append(error)
    elif ext == ".py":
        error = _check_python_syntax(settings, path)
        if error:
            errors.append(error)
    return records, errors


def _lang_for_filename(filename: str) -> str:
    ext = _normalise_extension(Path(filename).suffix)
    return {
        ".md": "markdown",
        ".txt": "text",
        ".py": "python",
        ".tex": "latex",
        ".html": "html",
        ".json": "json",
        ".csv": "csv",
        ".pdf": "pdf",
    }.get(ext, "text")


def _replacement_for(block: FileBlock, record: dict[str, Any], settings: RuntimeSettings) -> str:
    title = f"📄 Datei angelegt: {record.get('filename')}"
    if not bool(getattr(settings, "file_builder_show_source_code", True)):
        return title
    lang = _lang_for_filename(record.get("filename") or block.filename)
    content = block.content or ""
    try:
        saved_path = Path(record.get("path") or "")
        if _is_managed_doc_path(saved_path):
            content = saved_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        content = block.content or ""
    return f"{title}\n\n```{lang}\n{content.strip()}\n```"


def process_file_builder_output(
    settings: RuntimeSettings,
    user_input: str,
    output_text: str,
    context: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    info: dict[str, Any] = {
        "enabled": _enabled(settings),
        "records": [],
        "errors": [],
        "changed": False,
    }
    text = strip_file_builder_chat_cards(strip_file_builder_tags(output_text))
    thinking_text, visible_text = _strip_thinking_blocks_for_builder(text)
    if not _enabled(settings):
        return text, info

    blocks = _extract_blocks(visible_text, user_input, settings)
    if not blocks:
        return text, info

    max_bytes = max(1024, int(getattr(settings, "file_builder_max_bytes", 2_000_000) or 2_000_000))
    replacements: list[tuple[tuple[int, int], str]] = []
    for block in blocks:
        try:
            content = block.content or ""
            if len(content.encode("utf-8")) > max_bytes:
                raise ValueError(f"{block.filename}: Datei zu groß")
            records, errors = _save_content_bundle(
                settings,
                block.filename,
                content,
                block.source,
                {
                    "chat_id": (context or {}).get("chat_id"),
                    "user_preview": str(user_input or "")[:240],
                },
            )
            info["records"].extend(records)
            info["errors"].extend(errors)
            record = records[0]
            if block.source in {"bracket", "xml"} or bool(getattr(settings, "file_builder_replace_blocks", True)):
                replacements.append((block.span, _replacement_for(block, record, settings)))
        except Exception as exc:
            info["errors"].append(str(exc))

    cleaned = visible_text
    for span, replacement in sorted(replacements, key=lambda item: item[0][0], reverse=True):
        cleaned = cleaned[: span[0]] + replacement + cleaned[span[1] :]
    cleaned = _strip_empty_builder_artifact_fences(cleaned)

    if info["records"] and not replacements:
        names = ", ".join(record.get("filename", "") for record in info["records"])
        cleaned = f"{cleaned.rstrip()}\n\n📄 Docs angelegt: {names}".strip()

    docs_card = _docs_card_block(info["records"], info["errors"])
    if docs_card:
        cleaned = f"{cleaned.rstrip()}{docs_card}".strip()

    cleaned = _join_thinking_and_visible(thinking_text, cleaned)
    info["changed"] = cleaned != output_text
    return cleaned, info


def save_manual_doc(settings: RuntimeSettings, payload: dict[str, Any]) -> dict[str, Any]:
    filename = str(payload.get("filename") or "maat_note.txt")
    content = str(payload.get("content") or "")
    if not _enabled(settings):
        return {"ok": False, "error": "MAAT Docs/File Builder ist deaktiviert.", **file_builder_state(settings)}
    try:
        records, errors = _save_content_bundle(settings, filename, content, "manual", {"user_preview": "manual"})
        return {
            "ok": not errors,
            "error": "; ".join(errors) if errors else "",
            "record": records[0],
            "records": records,
            "errors": errors,
            **file_builder_state(settings, selected=records[0]["id"]),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), **file_builder_state(settings)}


def delete_doc(settings: RuntimeSettings, payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(payload.get("id") or payload.get("doc_id") or "").strip()
    if not doc_id:
        return {"ok": False, "error": "Keine Datei ausgewählt.", **file_builder_state(settings)}

    records = _read_index_all()
    target = next((record for record in records if str(record.get("id") or "") == doc_id), None)
    if target is None:
        return {"ok": False, "error": "Datei nicht gefunden.", **file_builder_state(settings)}

    path = Path(target.get("path") or "")
    if not _is_managed_doc_path(path):
        return {
            "ok": False,
            "error": "Datei liegt nicht im MAAT-Docs-Ordner und wurde nicht gelöscht.",
            **file_builder_state(settings, selected=doc_id),
        }

    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        return {
            "ok": False,
            "error": f"Datei konnte nicht gelöscht werden: {exc}",
            **file_builder_state(settings, selected=doc_id),
        }

    remaining = [record for record in records if str(record.get("id") or "") != doc_id]
    _write_index(remaining)
    return {
        "ok": True,
        "deleted": target,
        "deleted_file": True,
        **file_builder_state(settings),
    }


def _open_external_file(path: Path) -> dict[str, Any]:
    if not _is_managed_doc_path(path):
        return {"ok": False, "error": "Datei liegt nicht im MAAT-Docs-Ordner."}
    if sys.platform == "darwin" and shutil.which("open"):
        command = ["open", str(path)]
    elif os.name == "nt" and hasattr(os, "startfile"):
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
            return {"ok": True, "command": f"startfile {path}"}
        except OSError as exc:
            return {"ok": False, "error": f"Datei konnte nicht geöffnet werden: {exc}"}
    elif shutil.which("xdg-open"):
        command = ["xdg-open", str(path)]
    else:
        return {"ok": False, "error": "Kein Datei-Öffner gefunden."}

    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": f"Datei konnte nicht geöffnet werden: {exc}"}
    if completed.returncode != 0:
        return {"ok": False, "error": (completed.stderr or completed.stdout or "Datei konnte nicht geöffnet werden.").strip()}
    return {"ok": True, "command": " ".join(shlex.quote(part) for part in command)}


def open_doc(settings: RuntimeSettings, payload: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(payload.get("id") or payload.get("doc_id") or "").strip()
    if not doc_id:
        return {"ok": False, "error": "Keine Datei ausgewählt.", **file_builder_state(settings)}
    path = doc_path_by_id(doc_id)
    if path is None:
        return {"ok": False, "error": "Datei nicht gefunden.", **file_builder_state(settings)}
    result = _open_external_file(path)
    return {
        **result,
        "opened": str(path),
        **file_builder_state(settings, selected=doc_id),
    }


def doc_path_by_id(doc_id: str) -> Path | None:
    for record in _read_index(limit=500):
        if str(record.get("id") or "") == str(doc_id):
            path = Path(record.get("path") or "")
            if _is_managed_doc_path(path):
                return path
    return None


def _companion_pdf_for(record: dict[str, Any] | None, records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not record:
        return None
    ext = _normalise_extension(str(record.get("extension") or Path(record.get("path") or "").suffix))
    if ext == ".pdf":
        return record
    if ext != ".tex":
        return None
    try:
        tex_path = str(Path(record.get("path") or "").resolve())
    except OSError:
        tex_path = str(record.get("path") or "")
    stem = Path(record.get("path") or "").stem
    for item in records:
        item_ext = _normalise_extension(str(item.get("extension") or Path(item.get("path") or "").suffix))
        if item_ext != ".pdf":
            continue
        if str(item.get("source_tex") or "") == tex_path:
            return item
        if Path(item.get("path") or "").stem == stem:
            return item
    return None


def _read_preview(path: Path, max_chars: int) -> str:
    try:
        if _normalise_extension(path.suffix) == ".pdf":
            return "(PDF erzeugt. Nutze PDF öffnen oder Download.)"
        if path.stat().st_size > 4_000_000:
            return "(Datei ist zu groß für die Vorschau.)"
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError as exc:
        return f"(Vorschau konnte nicht gelesen werden: {exc})"


def file_builder_state(settings: RuntimeSettings, selected: str = "", limit: int = 80) -> dict[str, Any]:
    _ensure_dirs()
    records = _read_index(limit=limit)
    chosen = None
    if selected:
        chosen = next((record for record in records if str(record.get("id")) == str(selected)), None)
    if chosen is None and records:
        chosen = records[0]

    preview = ""
    if chosen:
        preview = _read_preview(Path(chosen["path"]), int(getattr(settings, "file_builder_preview_chars", 5000) or 5000))
    companion_pdf = _companion_pdf_for(chosen, _read_index(limit=500))
    return {
        "enabled": _enabled(settings),
        "inject_instructions": bool(getattr(settings, "file_builder_inject_instructions", True)),
        "replace_blocks": bool(getattr(settings, "file_builder_replace_blocks", True)),
        "show_source_code": bool(getattr(settings, "file_builder_show_source_code", True)),
        "auto_capture_fences": bool(getattr(settings, "file_builder_auto_capture_fences", True)),
        "compile_tex_pdf": bool(getattr(settings, "file_builder_compile_tex_pdf", True)),
        "python_syntax_check": bool(getattr(settings, "file_builder_python_syntax_check", True)),
        "python_run_enabled": bool(getattr(settings, "file_builder_python_run_enabled", True)),
        "python_run_in_terminal": bool(getattr(settings, "file_builder_python_run_in_terminal", True)),
        "inject_feedback": bool(getattr(settings, "file_builder_inject_feedback", True)),
        "debug": bool(getattr(settings, "file_builder_debug", False)),
        "preview_chars": int(getattr(settings, "file_builder_preview_chars", 5000) or 5000),
        "max_bytes": int(getattr(settings, "file_builder_max_bytes", 2_000_000) or 2_000_000),
        "root": str(DOCS_ROOT),
        "records": records,
        "selected": chosen,
        "companion_pdf": companion_pdf,
        "preview": preview,
        "status": f"MAAT Docs aktiv · {len(records)} Dateien · {DOCS_ROOT}",
    }


def command_docs(settings: RuntimeSettings, args: list[str]) -> str:
    state = file_builder_state(settings)
    records = state.get("records") or []
    if not args:
        lines = [
            "# MAAT Docs",
            state.get("status", ""),
            "",
            "Befehle:",
            "- `/maat docs` — letzte Dateien anzeigen",
            "- `/maat docs last` — letzte Datei mit Vorschau",
        ]
        for item in records[:8]:
            lines.append(f"- `{item.get('filename')}` · {item.get('created_at')} · {item.get('relative_path')}")
        return "\n".join(lines)
    if args[0].lower() == "last":
        selected = state.get("selected") or {}
        if not selected:
            return "Noch keine Docs-Datei vorhanden."
        preview = state.get("preview") or ""
        return f"# {selected.get('filename')}\n\n`{selected.get('path')}`\n\n```text\n{preview[:4000]}\n```"
    return "MAAT Docs Befehle: `/maat docs`, `/maat docs last`."
