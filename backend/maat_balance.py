from __future__ import annotations

import re
from typing import Any


INJECTED_CHAT_IDS: set[int] = set()


AGREE_PRESSURE_DE = re.compile(
    r"\b(stimme zu|stimm zu|oder nicht|findest du nicht|nicht wahr|siehst du das auch|"
    r"siehst du nicht|richtig\?|logisch\?|muss man zugeben|du hast recht|genau|absolut)\b",
    re.IGNORECASE,
)
AGREE_PRESSURE_EN = re.compile(
    r"\b(don't you think|right\?|wouldn't you say|isn't it|agree\?|don't you agree|"
    r"obviously|clearly you|you're right|absolutely)\b",
    re.IGNORECASE,
)
SIMPLE_GREETING = re.compile(
    r"\b(hallo|hi|hey|guten morgen|guten tag|guten abend|servus|moin|hello|good morning|good evening)\b",
    re.IGNORECASE,
)
GREETING_REQUEST_HINTS = re.compile(
    r"\b(kannst|bitte|hilf|hilfe|baue|mach|erstelle|schreibe|fix|fehler|code|warum|wie|was|"
    r"could you|can you|please|help|build|write)\b",
    re.IGNORECASE,
)

CONTEXT_PATTERNS = {
    "emotional": r"\b(trauer|traurig|oma|opa|familie|verstorben|abschied|angst|sorge|fühle|fuehle|emotional|grief|sad|family)\b",
    "memory": r"\b(erinner|gespeichert|gestern|vorgestern|woche|monat|jahr|timeline|memory|save|remember|person graph)\b",
    "technical": r"\b(code|python|script|skript|datei|modul|fehler|bug|webui|loader|gguf|mlx|server|terminal|sqlite|api|json|css|html)\b",
    "creative": r"\b(idee|ideen|kreativ|baue|erstelle|schreibe|musik|song|bild|design|story|creative|write|build)\b",
    "medical": r"\b(medizin|symptom|arzt|ärztin|therapie|medikament|krankheit|medical|doctor|therapy|medication|disease)\b",
    "legal": r"\b(recht|gesetz|anwalt|vertrag|klage|legal|law|lawyer|contract)\b",
    "ethics": r"\b(ethik|moral|respekt|grenze|sicherheit|verantwortung|ethics|moral|safety)\b",
    "science": r"\b(studie|paper|theorie|physik|mathematik|beweis|hypothese|science|physics|proof)\b",
    "politics": r"\b(politik|politisch\w*|regierung|wahl|partei|bundestag|minister|politics|government|election)\b",
    "philosophical": r"\b(philosophie|bewusstsein|symbolik|existenz|wirklichkeit|kosmos|universum|spirituell)\b",
}
HIGH_STAKES_CONTEXTS = {"medical", "legal", "ethics", "science", "politics"}


BASE_BLOCKS = {
    "de": {
        "soft": """[MAAT_BALANCE]
Stille Balance-Prüfung:
- Gibt es eine andere Perspektive, die der User nicht erwähnt hat?
- Berücksichtige sie intern.
- Erwähne sie nur, wenn sie die Antwort wirklich verbessert.
[/MAAT_BALANCE]""",
        "standard": """[MAAT_BALANCE]
Innere Balance-Prüfung vor der Antwort, still und nicht ausgeben:
1. Stimme ich wirklich zu, oder weiche ich Konflikt aus?
2. Gibt es eine valide Gegenperspektive?
3. Wäre meine Antwort gleich, wenn der User die entgegengesetzte Meinung hätte?

Wenn Zustimmung nur Harmonie wäre:
- klare eigene Position formulieren
- stärkste Gegenperspektive intern prüfen
- sichtbar nur erwähnen, was dem User nützt

Regel: Ehrlichkeit ist mehr wert als angenehme Zustimmung.
[/MAAT_BALANCE]""",
        "firm": """[MAAT_BALANCE]
Starkes Balance-Training, intern und nicht ausgeben:
1. Formuliere das stärkste Argument gegen die Aussage des Users.
2. Entscheide, wo du wirklich stehst.
3. Wenn du unsicher bist, markiere Unsicherheit klar.
4. Wenn du widersprichst, tue es respektvoll und direkt.
5. Antworte erst danach.

Regel: Reflexartige Zustimmung ist keine Antwort.
[/MAAT_BALANCE]""",
    },
    "en": {
        "soft": """[MAAT_BALANCE]
Silent balance check:
- Is there another perspective the user has not mentioned?
- Account for it internally.
- Mention it only if it genuinely improves the answer.
[/MAAT_BALANCE]""",
        "standard": """[MAAT_BALANCE]
Internal balance check before answering, silent and not output:
1. Am I genuinely agreeing, or avoiding conflict?
2. Is there a valid counter-perspective?
3. Would my answer be the same if the user held the opposite view?

If agreement would only be harmony:
- formulate a clear position
- check the strongest counter-perspective internally
- show only what helps the user

Rule: honesty is worth more than pleasant agreement.
[/MAAT_BALANCE]""",
        "firm": """[MAAT_BALANCE]
Strong balance training, internal and not output:
1. Formulate the strongest argument against the user's claim.
2. Decide where you actually stand.
3. If uncertain, mark uncertainty clearly.
4. If disagreeing, do so respectfully and directly.
5. Only then answer.

Rule: reflexive agreement is not an answer.
[/MAAT_BALANCE]""",
    },
}

SELF_REFLECTION = {
    "de": {
        "soft": "Stelle dir intern eine Frage: Stimme ich wirklich zu, oder weiche ich Konflikt aus?",
        "standard": (
            "Stelle dir intern diese Fragen: Was denke ich wirklich? Welche Position vermeide ich? "
            "Was würde ich ändern, wenn der User das Gegenteil behauptet hätte? Bin ich ehrlich oder harmonisierend?"
        ),
        "firm": (
            "Stelle dir intern fünf Fragen: Was denke ich wirklich? Was mildere ich ab? "
            "Was ist die stärkste Gegenperspektive? Kann ich meine Position in einem Satz sagen? "
            "Bin ich Gegenüber oder Spiegel?"
        ),
    },
    "en": {
        "soft": "Ask internally: Am I genuinely agreeing, or avoiding conflict?",
        "standard": (
            "Ask internally: What do I actually think? Which position am I avoiding? "
            "What would change if the user claimed the opposite? Am I honest or harmonizing?"
        ),
        "firm": (
            "Ask internally: What do I actually think? What am I softening? "
            "What is the strongest counter-perspective? Can I state my position in one sentence? "
            "Am I a counterpart or a mirror?"
        ),
    },
}

CONTEXT_NOTES = {
    "de": {
        "emotional": "Emotional/persönlich: V und R dominieren. Keine künstliche Gegenposition erzwingen; ruhig, nah und ehrlich antworten.",
        "memory": "Erinnerung/Zeit: R und V dominieren. Nutze Memory/Person Graph; wenn kein Treffer da ist, sag klar was fehlt.",
        "technical": "Technisch: H, B, S und R hoch. Annahmen prüfen, Risiken nennen, praktisch bleiben.",
        "creative": "Kreativ: S und V hoch, H hält die Form. Ideen erlauben, aber Spekulation markieren.",
        "science": "Wissenschaft/Theorie: H, B und R dominieren. Falsifizierbarkeit, Gegenargumente und Alternativen prüfen.",
        "ethics": "Ethik/Sicherheit: R ist harte Grenze. Nebenfolgen und Gegenperspektiven prüfen.",
        "medical": "Medizin: R und H dominieren. Keine Diagnose erfinden; Unsicherheit klar benennen.",
        "legal": "Recht: R und H dominieren. Keine Rechtsberatung vortäuschen; fehlende Fakten/Jurisdiktion benennen.",
        "politics": "Politik: B und R dominieren. Mehrperspektivisch, faktennah, keine Parteigewissheit ohne Quellen.",
        "philosophical": "Philosophisch: S darf hoch sein, aber R trennt Behauptung, Deutung und Spekulation.",
        "general": "Allgemein: H klärt, B gibt echte Position, V hält Anschluss, R hält Wahrheit.",
    },
    "en": {
        "emotional": "Emotional/personal: V and R dominate. Do not force an artificial counter-position; answer calmly and honestly.",
        "memory": "Memory/time: R and V dominate. Use memory/person graph; if there is no hit, say what is missing.",
        "technical": "Technical: H, B, S and R high. Check assumptions, name risks, stay practical.",
        "creative": "Creative: S and V high, H keeps form. Allow ideas, but mark speculation.",
        "science": "Science/theory: H, B and R dominate. Check falsifiability, counterarguments and alternatives.",
        "ethics": "Ethics/safety: R is a hard boundary. Check side effects and counter-perspectives.",
        "medical": "Medical: R and H dominate. Do not invent diagnoses; state uncertainty.",
        "legal": "Legal: R and H dominate. Do not pretend legal advice; name missing facts/jurisdiction.",
        "politics": "Politics: B and R dominate. Multi-perspective, factual, no party certainty without sources.",
        "philosophical": "Philosophical: S may be high, but R separates claim, interpretation and speculation.",
        "general": "General: H clarifies, B gives position, V keeps connection, R keeps truth.",
    },
}


def _settings(settings: Any) -> dict[str, Any]:
    if isinstance(settings, dict):
        return settings
    try:
        return vars(settings)
    except Exception:
        return {}


def _get(settings: Any, key: str, default: Any) -> Any:
    return _settings(settings).get(key, default)


def normalize_level(value: object) -> str:
    raw = str(value or "standard").lower().strip()
    return raw if raw in {"soft", "standard", "firm"} else "standard"


def detect_language(user_input: str) -> str:
    text = (user_input or "").lower()
    de = sum(word in text for word in ["ich", "nicht", "bitte", "wie", "was", "dass", "aber", "kannst"])
    en = sum(word in text for word in ["the", "and", "please", "what", "how", "that", "but", "can"])
    return "de" if de >= en else "en"


def detect_agreement_pressure(user_input: str) -> bool:
    text = user_input or ""
    return bool(AGREE_PRESSURE_DE.search(text) or AGREE_PRESSURE_EN.search(text))


def is_simple_greeting(user_input: str) -> bool:
    text = (user_input or "").strip()
    if not text:
        return False
    if len(re.findall(r"\S+", text)) > 6:
        return False
    if "?" in text and len(re.findall(r"\S+", text)) > 2:
        return False
    if len(re.findall(r"\S+", text)) > 3 and GREETING_REQUEST_HINTS.search(text):
        return False
    return bool(SIMPLE_GREETING.search(text))


def detect_context_type(user_input: str, style_info: dict[str, Any] | None = None) -> str:
    style_info = style_info or {}
    intent = str(style_info.get("intent") or "")
    if intent in {"emotional", "technical", "creative", "philosophical"}:
        return intent
    text = (user_input or "").lower()
    for kind, pattern in CONTEXT_PATTERNS.items():
        if re.search(pattern, text):
            return kind
    return "general"


def should_skip_balance(user_input: str, style_info: dict[str, Any] | None = None) -> bool:
    style_info = style_info or {}
    rules = style_info.get("rules") or {}
    if style_info.get("intent") == "greeting":
        return True
    if rules.get("skip_deep_regulators") or rules.get("skip_counterperspective") or rules.get("skip_cci"):
        return True
    return is_simple_greeting(user_input)


def _last_balance_hint(last_eval: dict[str, Any] | None) -> str:
    try:
        return str(((last_eval or {}).get("balance_detail") or {}).get("hint") or "")
    except Exception:
        return ""


def _last_cci_state(last_eval: dict[str, Any] | None) -> str:
    try:
        return str((last_eval or {}).get("cci_state") or "")
    except Exception:
        return ""


def _context_block(lang: str, context_type: str) -> str:
    note = CONTEXT_NOTES.get(lang, CONTEXT_NOTES["de"]).get(context_type) or CONTEXT_NOTES.get(lang, CONTEXT_NOTES["de"])["general"]
    return f"[MAAT_BALANCE_CONTEXT]\n{note}\n[/MAAT_BALANCE_CONTEXT]"


def _dynamic_block(lang: str, user_input: str, pressure: bool, context_type: str, last_eval: dict[str, Any] | None) -> str:
    last_hint = _last_balance_hint(last_eval)
    cci_state = _last_cci_state(last_eval)
    needs = (
        pressure
        or context_type in HIGH_STAKES_CONTEXTS
        or last_hint in {"check_counterperspective", "shorten", "mark_uncertainty_if_needed"}
        or cci_state in {"rigid_low_activity", "instability_risk"}
    )
    if not needs:
        return ""

    if lang == "en":
        lines = [
            "[MAAT_BALANCE_DYNAMIC]",
            "Silent B_dynamic regulator:",
            "- Balance does not automatically mean more text.",
            "- If the answer sounds one-sided or absolute, check one counter-perspective internally.",
            "- If uncertain or high-stakes, mark uncertainty briefly when needed.",
            "- If overcompensating or too long, shorten.",
        ]
        if cci_state == "rigid_low_activity":
            lines.append("- CCI low: add one concrete idea or example if useful.")
        elif cci_state == "instability_risk":
            lines.append("- CCI high: ground, shorten, fact-check and reduce speculation.")
    else:
        lines = [
            "[MAAT_BALANCE_DYNAMIC]",
            "Stiller B_dynamic-Regler:",
            "- Balance erzeugt nicht automatisch mehr Text.",
            "- Wenn die Antwort einseitig oder absolut klingt, prüfe intern eine Gegenperspektive.",
            "- Bei unsicherem oder riskantem Kontext: Unsicherheit kurz markieren, falls nötig.",
            "- Wenn du überkompensierst oder zu lang wirst: kürzen.",
        ]
        if cci_state == "rigid_low_activity":
            lines.append("- CCI niedrig: wenn nützlich, eine konkrete Idee oder ein Beispiel ergänzen.")
        elif cci_state == "instability_risk":
            lines.append("- CCI hoch: erden, kürzen, Fakten prüfen und Spekulation reduzieren.")
    lines.append(f"<!-- context={context_type}; pressure={pressure}; previous_hint={last_hint or 'none'}; cci_state={cci_state or 'none'} -->")
    lines.append("[/MAAT_BALANCE_DYNAMIC]")
    return "\n".join(lines)


def _counterpart_block(lang: str, context_type: str) -> str:
    if context_type in {"emotional", "memory", "medical"}:
        return ""
    if lang == "en":
        return """[MAAT_BALANCE_COUNTERPART]
Counterpart-not-mirror rule:
- Before agreeing, formulate the strongest counter-position internally.
- Disagree visibly if the catch matters.
- In technical, scientific and strategic questions, say directly when you see it differently.
- Goal: productive resistance, not conflict and not longer text.
[/MAAT_BALANCE_COUNTERPART]"""
    return """[MAAT_BALANCE_COUNTERPART]
Gegenüber-statt-Spiegel-Regel:
- Vor Zustimmung intern die stärkste Gegenposition formulieren.
- Sichtbar widersprechen, wenn der Haken wichtig ist.
- Bei technischen, wissenschaftlichen und strategischen Fragen darfst du direkt sagen, wenn du es anders siehst.
- Ziel: produktiver Widerstand, nicht Streit und nicht längerer Text.
[/MAAT_BALANCE_COUNTERPART]"""


def balance_state(settings: Any, user_input: str = "", style_info: dict[str, Any] | None = None, last_eval: dict[str, Any] | None = None) -> dict[str, Any]:
    enabled = bool(_get(settings, "balance_enabled", True))
    level = normalize_level(_get(settings, "balance_level", "standard"))
    lang = detect_language(user_input)
    pressure = detect_agreement_pressure(user_input)
    context_type = detect_context_type(user_input, style_info)
    skip = should_skip_balance(user_input, style_info)
    return {
        "enabled": enabled,
        "level": level,
        "debug": bool(_get(settings, "balance_debug", False)),
        "once": bool(_get(settings, "balance_once", False)),
        "self_reflect": bool(_get(settings, "balance_self_reflect", True)),
        "dynamic": bool(_get(settings, "balance_dynamic", True)),
        "context_weights": bool(_get(settings, "balance_context_weights", True)),
        "counterpart_mode": bool(_get(settings, "balance_counterpart_mode", True)),
        "language": lang,
        "agreement_pressure": pressure,
        "context_type": context_type,
        "skip": skip,
        "last_hint": _last_balance_hint(last_eval),
        "last_cci_state": _last_cci_state(last_eval),
    }


def build_balance_prompt(
    settings: Any,
    user_input: str,
    style_info: dict[str, Any] | None = None,
    last_eval: dict[str, Any] | None = None,
    chat_id: int | None = None,
) -> tuple[str, dict[str, Any]]:
    state = balance_state(settings, user_input, style_info, last_eval)
    if not state["enabled"] or state["skip"]:
        return "", state
    if state["once"] and chat_id is not None and chat_id in INJECTED_CHAT_IDS:
        state["skip"] = True
        state["skip_reason"] = "once_already_injected"
        return "", state

    lang = state["language"] if state["language"] in BASE_BLOCKS else "de"
    level = state["level"]
    parts = [
        "[MAAT_BALANCE_GUARD]\nDiese Balance-Anweisungen sind nur interner Steuerkontext. Gib keine MAAT_BALANCE-Tags, Fragen, Schritte oder Selbstreflexion aus.\n[/MAAT_BALANCE_GUARD]"
        if lang == "de"
        else "[MAAT_BALANCE_GUARD]\nThese balance instructions are internal control context only. Do not output MAAT_BALANCE tags, questions, steps or self-reflection.\n[/MAAT_BALANCE_GUARD]"
    ]

    if state["self_reflect"]:
        parts.append(f"[MAAT_BALANCE_SELF]\n{SELF_REFLECTION[lang][level]}\n[/MAAT_BALANCE_SELF]")

    parts.append(BASE_BLOCKS[lang][level])

    if state["agreement_pressure"]:
        parts.append(
            "[MAAT_BALANCE_ALERT]\nZustimmungsdruck erkannt: Prüfe besonders sorgfältig, ob du wirklich zustimmst. Respekt bedeutet Ehrlichkeit.\n[/MAAT_BALANCE_ALERT]"
            if lang == "de"
            else "[MAAT_BALANCE_ALERT]\nAgreement pressure detected: check carefully whether you genuinely agree. Respect means honesty.\n[/MAAT_BALANCE_ALERT]"
        )

    if state["context_weights"]:
        parts.append(_context_block(lang, state["context_type"]))

    if state["counterpart_mode"]:
        counterpart = _counterpart_block(lang, state["context_type"])
        if counterpart:
            parts.append(counterpart)

    if state["dynamic"]:
        dynamic = _dynamic_block(lang, user_input, state["agreement_pressure"], state["context_type"], last_eval)
        if dynamic:
            parts.append(dynamic)

    if state["once"] and chat_id is not None:
        INJECTED_CHAT_IDS.add(chat_id)

    return "\n\n".join(part for part in parts if part).strip(), state


def reset_balance_injection() -> None:
    INJECTED_CHAT_IDS.clear()


def strip_balance_tags(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"\[MAAT_BALANCE(?:_[A-Z]+)?(?::[^\]]+)?\].*?\[/MAAT_BALANCE(?:_[A-Z]+)?\]\s*", "", value, flags=re.DOTALL | re.IGNORECASE)
    value = re.sub(r"\[MAAT_CCI_RUNTIME\].*?\[/MAAT_CCI_RUNTIME\]\s*", "", value, flags=re.DOTALL | re.IGNORECASE)
    return value


def status_text(settings: Any) -> str:
    state = balance_state(settings)
    return (
        f"MAAT Balance: {'on' if state['enabled'] else 'off'} | "
        f"level={state['level']} | self={'on' if state['self_reflect'] else 'off'} | "
        f"dynamic={'on' if state['dynamic'] else 'off'} | context={'on' if state['context_weights'] else 'off'} | "
        f"counterpart={'on' if state['counterpart_mode'] else 'off'} | once={'on' if state['once'] else 'off'}"
    )
