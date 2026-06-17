from __future__ import annotations

import re
from typing import Any


GREETINGS = [
    "hallo",
    "hi",
    "hey",
    "guten morgen",
    "guten tag",
    "guten abend",
    "servus",
    "moin",
    "hello",
]

GREETING_REQUEST_HINTS = [
    "kannst",
    "bitte",
    "hilf",
    "hilfe",
    "baue",
    "mach",
    "erstelle",
    "schreibe",
    "fix",
    "fehler",
    "code",
    "warum",
    "wie",
    "was",
]

TECHNICAL = [
    "code",
    "python",
    "latex",
    "fehler",
    "bug",
    "programmieren",
    "script",
    "skript",
    "datei",
    "ordner",
    "modul",
    "loader",
    "webui",
    "textgen",
    "gguf",
    "mlx",
    "llama",
    "llama.cpp",
    "terminal",
    "install",
    "server",
    "api",
    "json",
    "yaml",
    "css",
    "html",
    "javascript",
]

ANALYSIS = [
    "was hältst du",
    "was haeltst du",
    "meinung",
    "einschätzung",
    "einschaetzung",
    "besser",
    "vergleich",
    "warum",
    "argument",
    "bewerte",
    "analyse",
    "risiko",
    "pros",
    "contras",
]

PHILOSOPHICAL = [
    "spirituell",
    "bewusstsein",
    "symbolik",
    "vision",
    "theorie",
    "philosophie",
    "ethik",
    "maat",
    "respekt",
    "harmonie",
    "balance",
    "schöpfung",
    "schoepfung",
    "verbundenheit",
    "kosmos",
    "universum",
]

CREATIVE = [
    "erstelle",
    "schreibe",
    "baue",
    "formuliere",
    "entwirf",
    "design",
    "idee",
    "ideen",
    "story",
    "text",
    "song",
    "musik",
    "generiere",
    "mach mir",
    "schreib",
    "zeichne",
]

EMOTIONAL = [
    "ich bin traurig",
    "ich bin wütend",
    "ich bin wuetend",
    "ich fühle",
    "ich fuehle",
    "mir geht es",
    "sorge",
    "angst",
    "verzweifelt",
    "vermiss",
    "trauere",
    "einsam",
    "weinen",
]

CASUAL = [
    "haha",
    "xd",
    ":d",
    "^^",
    ";)",
    ":)",
    "lol",
    "cool",
    "nice",
    "danke",
    "perfekt",
    "super",
]

STYLE_RULES: dict[str, dict[str, Any]] = {
    "greeting": {
        "max_words": 40,
        "structure": "minimal",
        "skip_deep_regulators": True,
        "skip_counterperspective": True,
        "skip_cci": True,
    },
    "technical": {"max_words": 350, "structure": "steps"},
    "analysis": {"max_words": 300, "structure": "balanced"},
    "philosophical": {"max_words": 400, "structure": "reflective"},
    "creative": {"max_words": 500, "structure": "free_but_clear"},
    "emotional": {"max_words": 220, "structure": "warm_direct"},
    "general": {"max_words": 180, "structure": "simple"},
}


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _has_any(text: str, markers: list[str]) -> bool:
    return any(marker in text for marker in markers)


def _is_greeting(text: str) -> bool:
    compact = (text or "").lower().strip()
    if not compact or _word_count(compact) > 6:
        return False
    if "?" in compact and _word_count(compact) > 2:
        return False
    if _word_count(compact) > 3 and _has_any(compact, GREETING_REQUEST_HINTS):
        return False
    return any(re.search(r"\b" + re.escape(greeting) + r"\b", compact) for greeting in GREETINGS)


def detect_intent(user_input: str) -> str:
    text = (user_input or "").lower().strip()
    if not text:
        return "general"
    if _is_greeting(text):
        return "greeting"
    if _has_any(text, EMOTIONAL):
        return "emotional"
    if _has_any(text, TECHNICAL):
        return "technical"
    if _has_any(text, ANALYSIS):
        return "analysis"
    if _has_any(text, CREATIVE):
        return "creative"
    if _has_any(text, PHILOSOPHICAL):
        return "philosophical"
    return "general"


def detect_tone_vector(user_input: str) -> dict[str, float]:
    text = (user_input or "").lower().strip()
    if not text:
        return {"technical": 0.0, "casual": 0.0, "emotional": 0.0, "creative": 0.0}

    def score(markers: list[str], extra: int = 0) -> float:
        hits = sum(1 for marker in markers if marker.lower() in text) + extra
        return round(min(1.0, hits / 3.0), 2)

    casual_extra = 1 if re.search(r"(?:xD|\^\^|:D|;\)|:\))", user_input or "") else 0
    return {
        "technical": score(TECHNICAL),
        "casual": score(CASUAL, casual_extra),
        "emotional": score(EMOTIONAL),
        "creative": score(CREATIVE),
    }


def _normalize(value: object, default: str, aliases: dict[str, str]) -> str:
    text = str(value or default).strip().lower()
    return aliases.get(text, default)


def normalize_emoji_mode(value: object) -> str:
    return _normalize(
        value,
        "few",
        {
            "none": "none",
            "no": "none",
            "off": "none",
            "aus": "none",
            "keine": "none",
            "0": "none",
            "few": "few",
            "low": "few",
            "wenig": "few",
            "wenige": "few",
            "1": "few",
            "many": "many",
            "viel": "many",
            "viele": "many",
            "high": "many",
            "2": "many",
        },
    )


def normalize_old_smiley_mode(value: object) -> str:
    return _normalize(
        value,
        "none",
        {
            "none": "none",
            "no": "none",
            "off": "none",
            "aus": "none",
            "keine": "none",
            "0": "none",
            "few": "few",
            "low": "few",
            "wenig": "few",
            "wenige": "few",
            "1": "few",
            "many": "many",
            "viel": "many",
            "viele": "many",
            "high": "many",
            "2": "many",
        },
    )


def normalize_tone_mode(value: object) -> str:
    return _normalize(
        value,
        "friendly",
        {
            "neutral": "neutral",
            "klar": "neutral",
            "sachlich": "neutral",
            "friendly": "friendly",
            "freundlich": "friendly",
            "warm": "friendly",
            "enthusiastic": "enthusiastic",
            "enthusiastisch": "enthusiastic",
            "begeistert": "enthusiastic",
            "scientific": "scientific",
            "wissenschaftlich": "scientific",
            "mentor": "mentor",
            "coach": "mentor",
            "philosophical": "philosophical",
            "philosophisch": "philosophical",
            "reflective": "philosophical",
        },
    )


def normalize_opening_mode(value: object) -> str:
    return _normalize(
        value,
        "varied",
        {
            "direct": "direct",
            "direkt": "direct",
            "none": "direct",
            "varied": "varied",
            "abwechslungsreich": "varied",
            "variabel": "varied",
            "auto": "varied",
            "warm": "warm",
            "personal": "personal",
            "persönlich": "personal",
            "persoenlich": "personal",
        },
    )


def normalize_density_mode(value: object) -> str:
    return _normalize(
        value,
        "normal",
        {
            "compact": "compact",
            "kompakt": "compact",
            "dense": "compact",
            "normal": "normal",
            "airy": "airy",
            "luftig": "airy",
            "locker": "airy",
        },
    )


def normalize_heading_mode(value: object) -> str:
    return _normalize(
        value,
        "simple",
        {
            "none": "none",
            "no": "none",
            "keine": "none",
            "off": "none",
            "simple": "simple",
            "einfach": "simple",
            "plain": "simple",
            "rich": "rich",
            "reich": "rich",
            "fancy": "rich",
        },
    )


def normalize_list_mode(value: object) -> str:
    return _normalize(
        value,
        "auto",
        {
            "none": "none",
            "no": "none",
            "keine": "none",
            "off": "none",
            "bullets": "bullets",
            "bullet": "bullets",
            "punkte": "bullets",
            "numbers": "numbers",
            "numbered": "numbers",
            "nummeriert": "numbers",
            "zahlen": "numbers",
            "auto": "auto",
            "automatisch": "auto",
        },
    )


def adaptive_tone_mode(base_tone: str, intent: str, tone_vector: dict[str, float], enabled: bool = True) -> str:
    base = normalize_tone_mode(base_tone)
    if not enabled:
        return base
    if intent == "technical" or tone_vector.get("technical", 0.0) >= 0.34:
        return "scientific"
    if intent == "emotional" or tone_vector.get("emotional", 0.0) >= 0.34:
        return "mentor"
    if intent == "creative" or tone_vector.get("creative", 0.0) >= 0.34:
        return "enthusiastic"
    if tone_vector.get("casual", 0.0) >= 0.34:
        return "friendly"
    if intent == "philosophical":
        return "philosophical"
    return base


def _tone_instruction(mode: str) -> str:
    return {
        "neutral": "Use a neutral, clear, calm tone.",
        "friendly": "Use a warm, friendly, direct tone. Keep it natural and not sugary.",
        "enthusiastic": "Use more energy in casual or creative answers, but avoid hype.",
        "scientific": "Use a precise, sober, evidence-aware tone.",
        "mentor": "Use a supportive mentor tone and explain steps clearly.",
        "philosophical": "Use a reflective, concept-oriented tone without empty mystification.",
    }[normalize_tone_mode(mode)]


def _emoji_instruction(mode: str) -> str:
    return {
        "none": "Do not use emojis.",
        "few": "Use at most one fitting emoji when it adds warmth; avoid emojis in technical or serious answers.",
        "many": "Use several fitting emojis in casual or playful answers; keep technical answers readable.",
    }[normalize_emoji_mode(mode)]


def _old_smiley_instruction(mode: str) -> str:
    return {
        "none": "Do not use ASCII smileys like xD, ;), :D, :), ^^.",
        "few": "In casual or playful answers, you may use at most one fitting ASCII smiley such as xD, ;), :D, :), or ^^.",
        "many": "In casual or playful answers, use old ASCII smileys more freely, for example xD, ;), :D, :), ^^.",
    }[normalize_old_smiley_mode(mode)]


def _opening_instruction(mode: str) -> str:
    return {
        "direct": "Start directly with the substance. Do not use routine greetings unless the user only greeted you.",
        "varied": "Do not start every answer with the same greeting or name. Vary naturally.",
        "warm": "Warm openings are allowed, but vary them. For technical answers, start directly after a short acknowledgement.",
        "personal": "Personal openings and the user's name are allowed more often, but never mechanically.",
    }[normalize_opening_mode(mode)]


def _density_instruction(mode: str) -> str:
    return {
        "compact": "Write compactly. Avoid extra blank lines and padding.",
        "normal": "Use normal spacing with short readable paragraphs.",
        "airy": "Use more line breaks and one idea per paragraph when helpful.",
    }[normalize_density_mode(mode)]


def _heading_instruction(mode: str) -> str:
    return {
        "none": "Do not use headings unless the user explicitly asks for them.",
        "simple": "Use short plain headings only when they help scanning.",
        "rich": "Use expressive short headings when helpful; keep technical answers restrained.",
    }[normalize_heading_mode(mode)]


def _list_instruction(mode: str) -> str:
    return {
        "none": "Avoid bullet and numbered lists; use concise prose.",
        "bullets": "Prefer bullet lists when there are multiple comparable points.",
        "numbers": "Prefer numbered lists for steps, sequences, and procedures.",
        "auto": "Choose prose, bullets, or numbered lists based on the task.",
    }[normalize_list_mode(mode)]


def style_state(settings: Any, user_input: str = "") -> dict[str, Any]:
    settings_dict = settings if isinstance(settings, dict) else vars(settings)
    intent = detect_intent(user_input or "")
    tone_vector = detect_tone_vector(user_input or "")
    base_tone = normalize_tone_mode(settings_dict.get("style_tone_mode", "friendly"))
    tone = adaptive_tone_mode(
        base_tone,
        intent,
        tone_vector,
        bool(settings_dict.get("style_tone_auto", True)),
    )
    rules = dict(STYLE_RULES.get(intent, STYLE_RULES["general"]))
    if intent == "greeting" and not settings_dict.get("style_greeting_override", True):
        rules["skip_deep_regulators"] = False
        rules["skip_counterperspective"] = False
        rules["skip_cci"] = False
    return {
        "enabled": bool(settings_dict.get("style_enabled", True)),
        "debug": bool(settings_dict.get("style_debug", False)),
        "intent": intent,
        "rules": rules,
        "tone_vector": tone_vector,
        "tone_mode": tone,
        "base_tone_mode": base_tone,
        "tone_auto": bool(settings_dict.get("style_tone_auto", True)),
        "emoji_mode": normalize_emoji_mode(settings_dict.get("style_emoji_mode", "few")),
        "old_smiley_mode": normalize_old_smiley_mode(settings_dict.get("style_old_smiley_mode", "none")),
        "opening_mode": normalize_opening_mode(settings_dict.get("style_opening_mode", "varied")),
        "density_mode": normalize_density_mode(settings_dict.get("style_density_mode", "normal")),
        "heading_mode": normalize_heading_mode(settings_dict.get("style_heading_mode", "simple")),
        "list_mode": normalize_list_mode(settings_dict.get("style_list_mode", "auto")),
    }


def build_style_prompt(settings: Any, user_input: str, visible_reasoning: bool = False) -> tuple[str, dict[str, Any]]:
    state = style_state(settings, user_input)
    if not state["enabled"]:
        return "", state

    intent = state["intent"]
    rules = state["rules"]
    if intent == "greeting":
        intent_text = (
            "Greeting mode has priority. Reply warmly and briefly, max 2 short sentences. "
            "No headings, bullets, project monologue, MAAT theory exposition, or visible self-reflection."
        )
    elif intent == "technical":
        intent_text = "Technical mode. Be precise, practical, and concise. Use steps or code blocks only when useful."
    elif intent == "analysis":
        intent_text = "Analysis mode. Give a clear position, relevant nuance, and a concise conclusion."
    elif intent == "philosophical":
        intent_text = "Reflective mode. Use calm structure and avoid overclaiming."
    elif intent == "creative":
        intent_text = "Creative mode. Be imaginative but clear. Give concrete output first."
    elif intent == "emotional":
        intent_text = "Emotional mode. Be warm, present, and direct. Do not over-structure."
    else:
        intent_text = "Natural mode. Answer directly and keep formatting light."

    lines = [
        f"MAAT Style guidance: intent={intent}, structure={rules.get('structure')}, max_words={rules.get('max_words')}.",
        intent_text,
        _tone_instruction(state["tone_mode"]),
        _opening_instruction(state["opening_mode"]),
        _density_instruction(state["density_mode"]),
        _heading_instruction(state["heading_mode"]),
        _list_instruction(state["list_mode"]),
        _emoji_instruction(state["emoji_mode"]),
        _old_smiley_instruction(state["old_smiley_mode"]),
        "Finish the current idea cleanly; do not truncate mid-thought.",
    ]
    if visible_reasoning:
        # Keep this compact so Qwen's visible thinking has less prompt text to quote.
        return " ".join(lines[:4]), state
    return "\n\n[MAAT_STYLE]\n" + "\n".join(lines) + "\n[/MAAT_STYLE]", state


ROUTINE_OPENING_RE = re.compile(
    r"^\s*(?:hey|hallo|hi|moin|guten morgen|guten tag|guten abend)\s+[\wÄÖÜäöüß-]{2,40}\b"
    r"\s*(?:xD|\^\^|:D|:\)|;\)|[^\w\s]{1,4})*"
    r"\s*[,.:;!\-–—]*\s*",
    re.IGNORECASE,
)


def _split_leading_codeblocks(text: str) -> tuple[str, str]:
    prefix = ""
    rest = text or ""
    while rest.startswith("```"):
        end = rest.find("\n```", 3)
        if end < 0:
            break
        close = rest.find("\n", end + 4)
        if close < 0:
            return prefix + rest, ""
        prefix += rest[: close + 1]
        rest = rest[close + 1 :]
    return prefix, rest


def _capitalize_start(text: str) -> str:
    match = re.match(r"^(\s*)([a-zäöü])", text or "")
    if not match:
        return text
    index = len(match.group(1))
    return text[:index] + text[index].upper() + text[index + 1 :]


def strip_routine_opening(user_input: str, output: str, settings: Any) -> str:
    state = style_state(settings, user_input)
    if not state["enabled"] or state["intent"] == "greeting":
        return output
    if state["opening_mode"] not in {"direct", "varied", "warm"}:
        return output
    prefix, rest = _split_leading_codeblocks(output or "")
    stripped = ROUTINE_OPENING_RE.sub("", rest, count=1)
    if stripped == rest:
        return output
    return prefix + _capitalize_start(stripped.lstrip())


def status_text(settings: Any, user_input: str = "") -> str:
    state = style_state(settings, user_input)
    return (
        f"MAAT Style: {'on' if state['enabled'] else 'off'} | "
        f"intent={state['intent']} | tone={state['tone_mode']} | "
        f"opening={state['opening_mode']} | density={state['density_mode']} | "
        f"headings={state['heading_mode']} | lists={state['list_mode']} | "
        f"emojis={state['emoji_mode']} | smileys={state['old_smiley_mode']}"
    )
