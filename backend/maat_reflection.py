from __future__ import annotations

import re
from typing import Any


LAST_REFLECTION: dict[str, Any] | None = None

SIMPLE_GREETING_RE = re.compile(
    r"\b(hallo|hi|hey|guten morgen|guten tag|guten abend|servus|moin|hello|good morning|good evening)\b",
    re.I,
)
REQUEST_HINT_RE = re.compile(
    r"\b(kannst|bitte|hilf|hilfe|baue|mach|erstelle|schreibe|fix|fehler|code|warum|wie|was|"
    r"could you|can you|please|help|build|write)\b",
    re.I,
)
RAW_SCORE_RE = re.compile(
    r"H\s*=\s*[\d.]+\s+B\s*=\s*[\d.]+\s+S\s*=\s*[\d.]+\s+V\s*=\s*[\d.]+\s+R\s*=\s*[\d.]+",
    re.I,
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _codeblock(text: str) -> str:
    return f"```text\n{str(text or '').strip()}\n```"


def is_simple_greeting(user_input: str) -> bool:
    text = str(user_input or "").strip()
    if not text:
        return False
    words = re.findall(r"\S+", text)
    if len(words) > 6:
        return False
    if "?" in text and len(words) > 2:
        return False
    if len(words) > 3 and REQUEST_HINT_RE.search(text):
        return False
    return bool(SIMPLE_GREETING_RE.search(text))


def maat_stability(H: float, B: float, S: float, V: float, R: float) -> dict[str, Any]:
    H = _safe_float(H)
    B = _safe_float(B)
    S = _safe_float(S)
    V = _safe_float(V)
    R = _safe_float(R)
    product = H * B * S * V
    geom = product**0.25 if product >= 0 else 0.0
    stability = min(R, geom)
    return {
        "H": H,
        "B": B,
        "S": S,
        "V": V,
        "R": R,
        "stability": stability,
        "text": f"H={H:.1f} B={B:.1f} S={S:.1f} V={V:.1f} R={R:.1f} → Stability={stability:.2f}",
    }


def build_reflection_prompt(settings: Any, user_input: str) -> str:
    if not getattr(settings, "reflection_enabled", True):
        return ""
    if not getattr(settings, "reflection_prompt_rule", True):
        return ""
    if is_simple_greeting(user_input):
        return ""
    return (
        "\n\n[MAAT_REFLECTION_RULE]\n"
        "Wenn du H, B, S, V, R oder Stability ausdrücklich erwähnst, nutze höchstens eine kompakte strukturierte Zeile. "
        "Keine wechselnde Score-Prosa, keine doppelten Score-Blöcke, keine internen Tags. "
        "Wenn das System Scores automatisch anzeigt, schreibe keine eigenen Scores.\n"
        "[/MAAT_REFLECTION_RULE]"
    )


def reflection_from_engine(engine_eval: dict[str, Any] | None) -> dict[str, Any] | None:
    if not engine_eval:
        return None
    try:
        result = maat_stability(
            engine_eval["H"],
            engine_eval["B"],
            engine_eval["S"],
            engine_eval["V"],
            engine_eval["R"],
        )
    except (KeyError, TypeError):
        return None
    result["diagnosis"] = str(engine_eval.get("diagnosis") or "")
    result["maat_value"] = engine_eval.get("maat_value")
    return result


def remember_reflection(result: dict[str, Any] | None) -> None:
    global LAST_REFLECTION
    if result:
        LAST_REFLECTION = result


def get_last_reflection() -> dict[str, Any] | None:
    return LAST_REFLECTION


def status_text(settings: Any) -> str:
    last = get_last_reflection()
    last_text = last["text"] if last else "None"
    return (
        f"MAAT Reflection: {'on' if getattr(settings, 'reflection_enabled', True) else 'off'} | "
        f"banner={'on' if getattr(settings, 'reflection_banner', False) else 'off'} | "
        f"mode={getattr(settings, 'reflection_mode', 'auto')} | "
        f"rule={'on' if getattr(settings, 'reflection_prompt_rule', True) else 'off'} | "
        f"last={last_text}"
    )


def report_lines(result: dict[str, Any] | None, mode: str = "auto") -> list[str]:
    if not result:
        return ["MAAT Reflection: noch keine Scores."]
    lines = [str(result.get("text") or "MAAT Reflection=n/a")]
    diagnosis = str(result.get("diagnosis") or "").split("|")[0].strip()
    if mode == "auto" and diagnosis:
        lines.append(diagnosis)
    return lines


def strip_raw_score_lines(text: str) -> str:
    lines_out: list[str] = []
    for line in str(text or "").splitlines():
        match = RAW_SCORE_RE.search(line)
        if not match:
            lines_out.append(line)
            continue
        rest = line[match.end() :].strip()
        rest = re.sub(r"^[\s→\-]+Stability\s*=\s*[\d.]+", "", rest, flags=re.I).strip()
        rest = re.sub(r"^[\s→\-]+", "", rest).strip()
        if rest:
            lines_out.append(rest)
    return "\n".join(lines_out).strip()


def apply_reflection_banner(
    settings: Any,
    user_input: str,
    output: str,
    engine_eval: dict[str, Any] | None,
    *,
    engine_debug_visible: bool = False,
) -> tuple[str, dict[str, Any] | None]:
    if not getattr(settings, "reflection_enabled", True):
        return output, None
    if is_simple_greeting(user_input):
        return output, None

    result = reflection_from_engine(engine_eval)
    remember_reflection(result)
    if not result:
        return output, None

    if engine_debug_visible:
        return output, result

    cleaned = strip_raw_score_lines(output)
    if not getattr(settings, "reflection_banner", False):
        return cleaned or output, result

    mode = str(getattr(settings, "reflection_mode", "auto") or "auto")
    banner = _codeblock("\n".join(report_lines(result, mode=mode)))
    return f"{banner}\n\n{cleaned or output}".strip(), result
