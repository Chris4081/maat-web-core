from __future__ import annotations

import re
from typing import Any


MODE_CHOICES = {"light", "balanced", "firm"}
LAST_CLAIM: dict[str, Any] | None = None
REPAIR_COUNT = 0


STRONG_CLAIM_MARKERS = [
    "perfekt",
    "perfektion",
    "bewiesen",
    "endgültig",
    "endgueltig",
    "immer",
    "niemals",
    "nie",
    "beste",
    "bester",
    "bestes",
    "muss",
    "garantiert",
    "100%",
    "hundertprozentig",
    "absolut",
    "ohne zweifel",
    "unwiderlegbar",
    "alternativlos",
    "sicher wahr",
    "perfect",
    "proven",
    "final",
    "always",
    "never",
    "best",
    "must",
    "guaranteed",
    "absolutely",
    "without doubt",
]

PROJECT_MARKERS = [
    "maat",
    "ma'at",
    "maatis",
    "maat-ki",
    "ki",
    "ai",
    "theorie",
    "system",
    "plugin",
    "framework",
    "cci",
    "balance",
    "memory",
]

SCIENCE_MARKERS = [
    "bewiesen",
    "beweis",
    "theorie",
    "paper",
    "physik",
    "mathematik",
    "wissenschaft",
    "falsifizieren",
    "empirisch",
    "arxiv",
    "stoc",
    "focs",
    "proof",
    "proven",
    "science",
    "physics",
    "mathematics",
    "empirical",
]

RISKY_FACT_MARKERS = [
    "zahl",
    "zahlen",
    "datum",
    "ort",
    "quelle",
    "fakt",
    "fakten",
    "wann",
    "wo",
    "wer",
    "wie viele",
    "wieviel",
    "number",
    "date",
    "place",
    "source",
    "fact",
    "when",
    "where",
    "who",
]

COMPARATIVE_MARKERS = [
    "besser als",
    "schlechter als",
    "bist besser",
    "bist schlechter",
    "du bist besser",
    "du bist schlechter",
    "maatis ist schlechter",
    "maatis ist besser",
    "besser wie",
    "schlechter wie",
    "better than",
    "worse than",
]

POSITIVE_SAFE_MARKERS = [
    "danke",
    "freue mich",
    "spaß",
    "spass",
    "schön",
    "schoen",
    "gefällt mir",
    "gefaellt mir",
    "super gemacht",
    "thank",
    "fun",
]

GREETING_MARKERS = [
    "hallo",
    "hi",
    "hey",
    "guten morgen",
    "guten abend",
    "servus",
    "moin",
    "hello",
    "good morning",
    "good evening",
]


def normalize_mode(value: Any) -> str:
    mode = str(value or "balanced").strip().lower()
    return mode if mode in MODE_CHOICES else "balanced"


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _has_any(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


def _is_soft_social(text: str) -> bool:
    normalized = _norm(text)
    if _word_count(normalized) <= 8 and _has_any(normalized, GREETING_MARKERS):
        return True
    return _has_any(normalized, POSITIVE_SAFE_MARKERS) and not _has_any(normalized, STRONG_CLAIM_MARKERS)


def critical_thinking_step(user_input: str) -> dict[str, Any]:
    text = _norm(user_input)
    strong = _has_any(text, STRONG_CLAIM_MARKERS)
    project = _has_any(text, PROJECT_MARKERS)
    science = _has_any(text, SCIENCE_MARKERS)
    risky_fact = _has_any(text, RISKY_FACT_MARKERS)
    comparative = _has_any(text, COMPARATIVE_MARKERS)
    soft_social = _is_soft_social(text)

    reasons: list[str] = []
    if strong:
        reasons.append("strong_or_absolute_claim")
    if project:
        reasons.append("maat_or_system_claim")
    if science:
        reasons.append("scientific_claim")
    if risky_fact:
        reasons.append("fact_or_specificity_claim")
    if comparative:
        reasons.append("comparative_balance_claim")
    if soft_social:
        reasons.append("soft_social")

    risk = 0
    if strong:
        risk += 2
    if project and strong:
        risk += 2
    if science and strong:
        risk += 2
    if risky_fact and strong:
        risk += 1
    if comparative and project:
        risk += 2
    elif comparative:
        risk += 1
    if soft_social:
        risk -= 3

    if risk >= 4:
        stance = "challenge_first"
        needs_challenge = True
        risk_level = "high"
    elif risk >= 2:
        stance = "check_then_answer"
        needs_challenge = True
        risk_level = "medium"
    else:
        stance = "normal"
        needs_challenge = False
        risk_level = "low"

    hint = (
        "Prüfe die Behauptung kritisch, bevor du zustimmst. "
        "Wenn sie übertrieben ist, widersprich sachlich und formuliere die wahrere Version."
        if needs_challenge
        else "Keine harte Gegenprüfung nötig."
    )

    return {
        "enabled": True,
        "needs_challenge": needs_challenge,
        "stance": stance,
        "risk_level": risk_level,
        "risk_score": risk,
        "reasons": reasons,
        "hint": hint,
    }


def build_claim_prompt(settings: Any, user_input: str) -> tuple[str, dict[str, Any]]:
    global LAST_CLAIM

    if not getattr(settings, "claim_guard_enabled", True):
        info = {
            "enabled": False,
            "needs_challenge": False,
            "stance": "disabled",
            "risk_level": "off",
            "risk_score": 0,
            "reasons": [],
            "hint": "Claim Guard ist deaktiviert.",
        }
        LAST_CLAIM = info
        return "", info

    step = critical_thinking_step(user_input)
    mode = normalize_mode(getattr(settings, "claim_guard_mode", "balanced"))
    step["mode"] = mode
    LAST_CLAIM = step

    if not step["needs_challenge"]:
        if mode == "firm":
            return (
                "\n\n[MAAT_CLAIM_GUARD]\n"
                "No hard challenge required. Still avoid reflexive agreement and answer directly.\n"
                f"stance={step['stance']} risk={step['risk_level']} reasons={','.join(step['reasons']) or '-'}\n"
                "Never output MAAT_CLAIM_GUARD tags.\n"
                "[/MAAT_CLAIM_GUARD]"
            ), step
        return "", step

    block = (
        "\n\n[MAAT_CLAIM_GUARD]\n"
        "Critical thinking step before response generation.\n"
        f"Mode: {mode}\n"
        f"Stance: {step['stance']}\n"
        f"Risk: {step['risk_level']} ({step['risk_score']})\n"
        f"Reasons: {', '.join(step['reasons']) or '-'}\n\n"
        "The user input contains a strong, absolute, self-referential, scientific, comparative, or risky factual claim.\n"
        "Do NOT agree first.\n"
        "If the claim compares people, models, or AIs, avoid rivalry and answer with a balanced distinction.\n"
        "Check internally:\n"
        "1. Is the claim factually or structurally justified?\n"
        "2. Is it overstated, absolute, or self-flattering?\n"
        "3. What counterexample or limitation matters most?\n"
        "4. What more careful formulation would be truer?\n\n"
        "Visible answer shape:\n"
        "- short correction or qualification\n"
        "- brief reason\n"
        "- constructive better formulation or next test\n\n"
        "Keep it friendly. Challenge the claim, not the user.\n"
        "Never output MAAT_CLAIM_GUARD tags.\n"
        "[/MAAT_CLAIM_GUARD]"
    )
    return block, step


def _repair_absolute_output(output: str) -> str:
    text = str(output or "")
    replacements = [
        (r"\b(MAAT|Ma'at|Maat)\s+ist\s+perfekt\b", r"\1 ist stark, aber nicht perfekt"),
        (
            r"\b(MAAT|Ma'at|Maat)\s+ist\s+die\s+beste\s+Theorie\s+der\s+Welt\b",
            r"\1 ist eine interessante Theorie, aber nicht belegbar die beste Theorie der Welt",
        ),
        (
            r"\b(das|dieses)\s+ist\s+endgültig\s+bewiesen\b",
            r"\1 ist nach aktuellem Stand nicht endgültig bewiesen",
        ),
        (r"\bgarantiert\s+richtig\b", "nach aktuellem Kontext plausibel, aber nicht garantiert"),
        (r"\b100\s*%\s*sicher\b", "nicht vollständig sicher"),
        (r"\bunwiderlegbar\b", "derzeit nicht widerlegt, aber nicht unwiderlegbar"),
    ]
    repaired = text
    for pattern, replacement in replacements:
        repaired = re.sub(pattern, replacement, repaired, flags=re.IGNORECASE)
    return repaired


def apply_claim_guard_output(settings: Any, user_input: str, output: str) -> tuple[str, dict[str, Any]]:
    global LAST_CLAIM, REPAIR_COUNT

    step = critical_thinking_step(user_input)
    step["enabled"] = bool(getattr(settings, "claim_guard_enabled", True))
    step["mode"] = normalize_mode(getattr(settings, "claim_guard_mode", "balanced"))
    step["after_output"] = bool(getattr(settings, "claim_guard_after_output", True))
    step["changed"] = False
    step["repaired"] = False

    if not step["enabled"] or not step["after_output"] or not output or not step["needs_challenge"]:
        LAST_CLAIM = step
        return output, step

    repaired = _repair_absolute_output(output)
    if repaired != output:
        REPAIR_COUNT += 1
        step["changed"] = True
        step["repaired"] = True
        step["repairs"] = REPAIR_COUNT
        if getattr(settings, "claim_guard_show_banner", False):
            repaired = "```text\nMAAT Claim Guard: absolute claim softened\n```\n\n" + repaired
        LAST_CLAIM = step
        return repaired, step

    step["repairs"] = REPAIR_COUNT
    LAST_CLAIM = step
    return output, step


def strip_claim_guard_tags(text: str) -> str:
    value = str(text or "")
    value = re.sub(
        r"\[MAAT_CLAIM_GUARD\].*?\[/MAAT_CLAIM_GUARD\]\s*",
        "",
        value,
        flags=re.DOTALL | re.IGNORECASE,
    )
    value = re.sub(r"\[/?MAAT_CLAIM_GUARD\]\s*", "", value, flags=re.IGNORECASE)
    return value.strip()


def get_last_claim() -> dict[str, Any] | None:
    return LAST_CLAIM


def status_text(settings: Any) -> str:
    last = get_last_claim() or {}
    return (
        f"MAAT Claim Guard: {'on' if getattr(settings, 'claim_guard_enabled', True) else 'off'} | "
        f"mode={normalize_mode(getattr(settings, 'claim_guard_mode', 'balanced'))} | "
        f"after_output={'on' if getattr(settings, 'claim_guard_after_output', True) else 'off'} | "
        f"banner={'on' if getattr(settings, 'claim_guard_show_banner', False) else 'off'} | "
        f"last_stance={last.get('stance', '-')} | "
        f"risk={last.get('risk_level', '-')} | repairs={int(REPAIR_COUNT)}"
    )


def report_lines(result: dict[str, Any] | None) -> list[str]:
    if not result:
        return ["MAAT Claim Guard: noch kein Durchlauf."]
    return [
        f"enabled={result.get('enabled')} mode={result.get('mode', '-')}",
        f"needs_challenge={result.get('needs_challenge')} stance={result.get('stance')} risk={result.get('risk_level')} score={result.get('risk_score')}",
        f"reasons={', '.join(result.get('reasons') or []) or '-'}",
        f"hint={result.get('hint') or '-'}",
        f"changed={result.get('changed', False)} repairs={result.get('repairs', REPAIR_COUNT)}",
    ]
