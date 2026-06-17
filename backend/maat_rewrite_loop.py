from __future__ import annotations

import re
from typing import Any


LAST_REWRITE: dict[str, Any] | None = None

MODE_CHOICES = {"light", "balanced", "strict"}


PRACTICAL_MARKERS = [
    "wie ",
    "warum klappt",
    "fix ",
    "code",
    " bug",
    "fehler",
    "problem",
    "besser antworten",
    "verbessern",
    "installier",
    "starte",
    "zeig mir",
    "debug",
    "install",
    "show me",
    "build",
    "make it",
    "create",
    "run ",
    "configure",
    "schreib mir",
    "erstelle",
    "generiere",
    "liste",
]

PHILOSOPHICAL_OVERRIDE = [
    "paradox",
    "quantenphysik",
    "bewusstsein",
    "schroedinger",
    "schrödinger",
    "freiheit",
    "existenz",
    "loese das",
    "löse das",
    "loesung fuer das",
    "lösung für das",
    "consciousness",
    "quantum",
    "philosophy",
]

PHILOSOPHICAL_MARKERS = [
    "was ist",
    "wer bist",
    "bewusstsein",
    "freiheit",
    "sinn",
    "jenseits",
    "bedeutung",
    "existenz",
    "philosophie",
    "what is",
    "who are",
    "consciousness",
    "freedom",
    "meaning",
]

STRUCTURED_REQUEST_MARKERS = [
    "code",
    "python",
    "javascript",
    "typescript",
    "html",
    "css",
    "json",
    "yaml",
    "script",
    "programmier",
    "programmiere",
    "program",
    "klasse",
    "funktion",
    "latex",
    "tex",
    "formel",
    "gleichung",
    "equation",
    "mathe",
    "berechnung",
    "calculator",
]

SAFETY_REPLY_PREFIXES = (
    "ich kann das nicht sicher",
    "ich weiß das nicht sicher",
    "ich weiss das nicht sicher",
    "ich bin mir nicht sicher",
    "ich könnte hier konkrete",
    "ich koennte hier konkrete",
    "ich möchte dir nichts falsches",
    "ich moechte dir nichts falsches",
    "soweit ich mich",
    "das tue ich nicht",
)

DRIFT_PATTERNS = [
    r"\bich sp[üu]re\b",
    r"\bi feel\b",
    r"\bechte frage hinter\b",
    r"\breal question behind\b",
    r"\bwas ist die (eigentliche|tiefere|wahre)\b",
    r"\betwas neues entsteht\b",
    r"\btanz zwischen\b",
]

POETIC_OPENERS = [
    "ich bin die frage",
    "bewusstsein ist das, was",
    "die wahre frage",
]


def normalize_mode(value: Any) -> str:
    mode = str(value or "light").strip().lower()
    return mode if mode in MODE_CHOICES else "light"


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "ja", "on", "an"}


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _is_philosophical(user_input: str) -> bool:
    text = _norm(user_input)
    return any(marker in text for marker in PHILOSOPHICAL_MARKERS)


def _is_practical(user_input: str) -> bool:
    text = _norm(user_input)
    if any(marker in text for marker in PHILOSOPHICAL_OVERRIDE):
        return False
    return any(marker in text for marker in PRACTICAL_MARKERS)


def _looks_like_safety_reply(text: str) -> bool:
    return str(text or "").lower().strip().startswith(SAFETY_REPLY_PREFIXES)


def _requests_structured_output(user_input: str) -> bool:
    text = _norm(user_input)
    return any(marker in text for marker in STRUCTURED_REQUEST_MARKERS)


def _contains_structured_output(text: str) -> bool:
    value = str(text or "")
    if "```" in value:
        return True
    if re.search(r"(?s)\\\[(.+?)\\\]|\\\((.+?)\\\)|\$\$(.+?)\$\$", value):
        return True
    if re.search(r"\\begin\{(?:equation|align|matrix|cases|array|pmatrix|bmatrix)\}", value):
        return True
    if re.search(r"(?m)^\s*(?:import|from\s+\S+\s+import|class\s+\w+|def\s+\w+|function\s+\w+|const\s+\w+\s*=|let\s+\w+\s*=|var\s+\w+\s*=)\b", value):
        return True
    if re.search(r"(?m)^\s*(?:for|while|if|elif|else|try|except|with)\b.*:\s*$", value):
        return True
    return False


def _strip_over_poetic_lines(text: str) -> str:
    lines = str(text or "").splitlines()
    cleaned = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            cleaned.append(line)
            continue
        if not in_code and any(opener in line.lower() for opener in POETIC_OPENERS):
            continue
        cleaned.append(line)
    result = "\n".join(cleaned).strip()
    return result if result else text


def _remove_drift_sentences(text: str) -> str:
    value = str(text or "")
    if "```" in value:
        return _strip_over_poetic_lines(value)

    sentences = re.split(r"(?<=[.!?])\s+", value)
    kept = []
    for sentence in sentences:
        if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in DRIFT_PATTERNS):
            continue
        kept.append(sentence.strip())
    cleaned = " ".join(item for item in kept if item).strip()
    if cleaned and cleaned != value.strip() and len(cleaned.split()) >= 3:
        return cleaned
    return _strip_over_poetic_lines(value)


def _shorten_text(text: str, max_sentences: int, *, enabled: bool) -> str:
    if not enabled:
        return text
    value = str(text or "")
    if "```" in value:
        return value
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", value) if part.strip()]
    return " ".join(parts[:max_sentences]) if len(parts) > max_sentences else value


def _fix_harmony(text: str, *, strong: bool, trim: bool) -> str:
    cleaned = _strip_over_poetic_lines(text)
    return _shorten_text(cleaned, 3 if strong else 5, enabled=trim)


def _fix_balance(text: str, user_input: str, *, strong: bool, r_val: float) -> str:
    value = str(text or "")
    if _looks_like_safety_reply(value):
        return value
    if r_val > 7.5 and strong:
        value = re.sub(r"\b(vielleicht|eventuell|koennte|könnte)\b", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s{2,}", " ", value).strip()
    if not _is_philosophical(user_input):
        stripped = value.lstrip()
        if stripped and not stripped.lower().startswith(("kurz gesagt", "die antwort", "konkret")):
            value = "Kurz gesagt: " + stripped
    return value


def _fix_respect(text: str) -> str:
    value = str(text or "").strip()
    if _looks_like_safety_reply(value):
        return value
    if value.lower().startswith("ich antworte darauf ehrlich"):
        return value
    return "Ich antworte darauf ehrlich und mit Vorsicht:\n\n" + value


def _apply_force_direct(text: str, trim: bool) -> str:
    cleaned = _remove_drift_sentences(text)
    return _shorten_text(cleaned, 4, enabled=trim)


def _choose_action(
    settings: Any,
    user_input: str,
    output: str,
    engine_eval: dict[str, Any] | None,
) -> dict[str, Any]:
    if not _safe_bool(getattr(settings, "rewrite_enabled", True), True):
        return {"action": "disabled", "reason": "rewrite_off", "values": {}, "issues": []}

    if not str(output or "").strip():
        return {"action": "pass", "reason": "empty_output", "values": {}, "issues": []}

    if _looks_like_safety_reply(output):
        return {"action": "pass", "reason": "safety_reply", "values": {}, "issues": []}

    if _requests_structured_output(user_input) or _contains_structured_output(output):
        return {"action": "pass", "reason": "structured_output_protected", "values": {}, "issues": []}

    if _is_practical(user_input):
        return {"action": "force_direct", "reason": "practical_question", "values": {}, "issues": []}

    engine = engine_eval or {}
    H = _safe_float(engine.get("H"), 7.0)
    B = _safe_float(engine.get("B"), 7.0)
    S = _safe_float(engine.get("S"), 7.0)
    V = _safe_float(engine.get("V"), 7.0)
    R = _safe_float(engine.get("R"), 7.0)

    weak = _safe_float(getattr(settings, "rewrite_field_weak", 6.2), 6.2)
    strong = _safe_float(getattr(settings, "rewrite_field_strong", 5.0), 5.0)
    r_min = _safe_float(getattr(settings, "rewrite_r_min", 7.0), 7.0)

    issues: list[tuple[str, bool]] = []
    if R < r_min:
        issues.append(("respect", True))
    for field, score in sorted(
        {"harmony": H, "balance": B, "creativity": S, "connection": V}.items(),
        key=lambda item: item[1],
    ):
        if score < strong:
            issues.append((field, True))
        elif score < weak:
            issues.append((field, False))

    if not issues:
        return {
            "action": "pass",
            "reason": "all_good",
            "values": {"H": H, "B": B, "S": S, "V": V, "R": R},
            "issues": [],
        }

    mode = normalize_mode(getattr(settings, "rewrite_mode", "light"))
    max_fixes = 1 if mode == "light" else 2 if mode == "balanced" else 3
    return {
        "action": "multi_fix",
        "reason": "weak_fields",
        "values": {"H": H, "B": B, "S": S, "V": V, "R": R},
        "issues": issues[:max_fixes],
    }


def _apply_multi_fix(settings: Any, user_input: str, output: str, issues: list[tuple[str, bool]], r_val: float) -> str:
    trim = _safe_bool(getattr(settings, "rewrite_trim_outputs", False), False)
    value = str(output or "")
    for field, strong in issues:
        if field == "respect":
            value = _fix_respect(value)
        elif field == "harmony":
            value = _fix_harmony(value, strong=strong, trim=trim)
        elif field == "balance":
            value = _fix_balance(value, user_input, strong=strong, r_val=r_val)
        elif field in {"creativity", "connection"}:
            # Style, Balance and Feedback handle these silently. The rewrite loop
            # does not append repeated filler sentences.
            value = value
    return value


def apply_rewrite_loop(
    settings: Any,
    user_input: str,
    output: str,
    engine_eval: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    global LAST_REWRITE

    decision = _choose_action(settings, user_input, output, engine_eval)
    trim = _safe_bool(getattr(settings, "rewrite_trim_outputs", False), False)
    action = decision.get("action")
    new_output = str(output or "")

    if action == "force_direct":
        new_output = _apply_force_direct(new_output, trim)
    elif action == "multi_fix":
        new_output = _apply_multi_fix(
            settings,
            user_input,
            new_output,
            decision.get("issues") or [],
            r_val=_safe_float((decision.get("values") or {}).get("R"), 8.0),
        )

    changed = new_output != str(output or "")
    info = {
        "enabled": _safe_bool(getattr(settings, "rewrite_enabled", True), True),
        "mode": normalize_mode(getattr(settings, "rewrite_mode", "light")),
        "trim_outputs": trim,
        "action": action,
        "reason": decision.get("reason"),
        "changed": changed,
        "issues": [
            {"field": field, "strong": strong}
            for field, strong in (decision.get("issues") or [])
        ],
        "values": decision.get("values") or {},
    }

    LAST_REWRITE = info
    return (new_output if changed else str(output or "")), info


def get_last_rewrite() -> dict[str, Any] | None:
    return LAST_REWRITE


def status_text(settings: Any) -> str:
    last = get_last_rewrite()
    last_text = "None"
    if last:
        if last.get("action") == "multi_fix":
            issues = ", ".join(
                f"{item.get('field')}({'S' if item.get('strong') else 'L'})"
                for item in last.get("issues", [])
            )
            last_text = f"multi_fix[{issues or '-'}]"
        else:
            last_text = str(last.get("action") or "pass")
    return (
        f"MAAT Rewrite: {'on' if getattr(settings, 'rewrite_enabled', True) else 'off'} | "
        f"mode={normalize_mode(getattr(settings, 'rewrite_mode', 'light'))} | "
        f"trim={'on' if getattr(settings, 'rewrite_trim_outputs', False) else 'off'} | "
        f"weak={_safe_float(getattr(settings, 'rewrite_field_weak', 6.2), 6.2):.1f} | "
        f"strong={_safe_float(getattr(settings, 'rewrite_field_strong', 5.0), 5.0):.1f} | "
        f"Rmin={_safe_float(getattr(settings, 'rewrite_r_min', 7.0), 7.0):.1f} | "
        f"last={last_text}"
    )


def report_lines(result: dict[str, Any] | None) -> list[str]:
    if not result:
        return ["MAAT Rewrite: noch kein Durchlauf."]
    lines = [
        f"enabled={result.get('enabled')} mode={result.get('mode')} trim={result.get('trim_outputs')}",
        f"action={result.get('action')} reason={result.get('reason')} changed={result.get('changed')}",
    ]
    issues = result.get("issues") or []
    if issues:
        lines.append(
            "issues="
            + ", ".join(
                f"{item.get('field')}({'strong' if item.get('strong') else 'light'})"
                for item in issues
            )
        )
    values = result.get("values") or {}
    if values:
        lines.append(
            "scores="
            + " ".join(f"{key}={_safe_float(values.get(key), 0):.1f}" for key in ["H", "B", "S", "V", "R"])
        )
    return lines
