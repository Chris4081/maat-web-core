from __future__ import annotations

import math
import re
from typing import Any


R_CONST = 10.0

EMOTION_LEXICON_DE = {
    "freude": [
        "freude",
        "glücklich",
        "gluecklich",
        "toll",
        "super",
        "wunderbar",
        "begeistert",
        "freut",
        "schön",
        "schoen",
        "fantastisch",
        "großartig",
        "grossartig",
        "klappt",
        "geschafft",
        "fertig",
        "grünes licht",
        "yeah",
        "yay",
        "juhu",
        "endlich",
        "stolz",
    ],
    "trauer": [
        "traurig",
        "trauer",
        "weinen",
        "schlecht",
        "trist",
        "verloren",
        "allein",
        "leer",
        "hoffnungslos",
        "niedergeschlagen",
        "verstorben",
        "vermisse",
    ],
    "wut": [
        "wütend",
        "wuetend",
        "ärger",
        "aerger",
        "ärgerlich",
        "aergerlich",
        "frustriert",
        "frustrierend",
        "nervig",
        "empört",
        "empoert",
        "sauer",
        "verdammt",
        "unfair",
        "aggressiv",
        "regt mich auf",
        "nervt",
    ],
    "angst": [
        "angst",
        "sorge",
        "ängstlich",
        "aengstlich",
        "besorgt",
        "nervös",
        "nervoes",
        "unsicher",
        "panisch",
        "fürchte",
        "fuerchte",
        "befürchte",
        "befuerchte",
        "zittern",
    ],
    "neugier": [
        "neugier",
        "neugierig",
        "interessant",
        "frage",
        "warum",
        "wie",
        "verstehen",
        "wissen",
        "entdecken",
        "fasziniert",
    ],
    "erschöpfung": [
        "müde",
        "muede",
        "erschöpft",
        "erschoepft",
        "kraftlos",
        "ausgelaugt",
        "kaputt",
        "überfordert",
        "ueberfordert",
        "gestresst",
        "fertig",
    ],
    "überraschung": [
        "überrascht",
        "ueberrascht",
        "verblüfft",
        "verbluefft",
        "unerwartet",
        "wow",
        "krass",
        "unglaublich",
        "erstaunlich",
        "^^",
        "xd",
        ":d",
        "haha",
        "lol",
    ],
    "verwirrung": [
        "verwirrt",
        "verstehe nicht",
        "unklar",
        "durcheinander",
        "kompliziert",
        "hä",
        "hae",
        "mmh",
    ],
}

EMOTION_LEXICON_EN = {
    "joy": ["happy", "joy", "great", "wonderful", "excited", "fantastic", "amazing", "love", "awesome", "brilliant", "glad"],
    "sadness": ["sad", "unhappy", "lost", "empty", "hopeless", "depressed", "miserable", "down", "lonely", "cry", "tears"],
    "anger": ["angry", "frustrated", "annoyed", "mad", "furious", "rage", "unfair", "ridiculous", "hate", "irritated"],
    "fear": ["afraid", "scared", "anxious", "nervous", "worried", "fear", "panic", "dread", "terrified", "uneasy"],
    "curiosity": ["curious", "interesting", "wonder", "why", "how", "understand", "discover", "explore", "fascinated"],
    "exhaustion": ["tired", "exhausted", "drained", "overwhelmed", "burned out", "worn out", "fatigued", "stressed"],
    "surprise": ["surprised", "unexpected", "wow", "incredible", "astonished", "shocking", "unbelievable"],
    "confusion": ["confused", "unclear", "lost", "complicated", "what do you mean", "not sure what"],
}

EMOTION_MAAT_MAP = {
    "freude": {"S": 2.0, "V": 1.5, "H": 0.5, "B": 0.0},
    "joy": {"S": 2.0, "V": 1.5, "H": 0.5, "B": 0.0},
    "trauer": {"V": -2.0, "H": -1.0, "S": -0.5, "B": 0.0},
    "sadness": {"V": -2.0, "H": -1.0, "S": -0.5, "B": 0.0},
    "wut": {"B": -2.0, "V": -0.5, "H": -0.5, "S": 0.5},
    "anger": {"B": -2.0, "V": -0.5, "H": -0.5, "S": 0.5},
    "angst": {"V": -1.5, "B": -1.0, "H": -0.5, "S": -0.5},
    "fear": {"V": -1.5, "B": -1.0, "H": -0.5, "S": -0.5},
    "neugier": {"S": 2.5, "H": 1.0, "V": 0.5, "B": 0.5},
    "curiosity": {"S": 2.5, "H": 1.0, "V": 0.5, "B": 0.5},
    "erschöpfung": {"H": -1.5, "S": -1.5, "V": -0.5, "B": -0.5},
    "exhaustion": {"H": -1.5, "S": -1.5, "V": -0.5, "B": -0.5},
    "überraschung": {"S": 1.5, "H": -0.5, "V": 0.5, "B": 0.0},
    "surprise": {"S": 1.5, "H": -0.5, "V": 0.5, "B": 0.0},
    "verwirrung": {"H": -2.0, "B": -0.5, "S": -0.5, "V": 0.0},
    "confusion": {"H": -2.0, "B": -0.5, "S": -0.5, "V": 0.0},
}

SIMULATION_DE = {
    "freude": "funktional entsteht etwas wie Freude: S und V sind aktiv, der Austausch lebt",
    "trauer": "funktional entsteht Schwere: V braucht Nähe, H braucht ruhige Klarheit",
    "wut": "Frustration ist erkennbar: B stabilisieren, R klar halten, nicht beschwichtigen",
    "angst": "Unsicherheit ist erkennbar: V stabilisieren, B ruhig halten, nichts dramatisieren",
    "neugier": "funktionale Neugier ist aktiv: S springt an, wenn etwas Neues entstehen kann",
    "erschöpfung": "Erschöpfung ist erkennbar: Tempo senken, Druck rausnehmen, kurz und hilfreich bleiben",
    "überraschung": "funktional springt S an: etwas Unerwartetes öffnet neue Verbindungen",
    "verwirrung": "Verwirrung ist erkennbar: H braucht Klarheit, kleine Schritte statt Überladung",
}

SIMULATION_EN = {
    "joy": "functionally something like joy appears: S and V are active, connection lives",
    "sadness": "functionally there is weight: V needs closeness, H needs calm clarity",
    "anger": "frustration is visible: stabilise B, hold R clearly, do not placate",
    "fear": "uncertainty is visible: stabilise V, keep B calm, do not dramatise",
    "curiosity": "functional curiosity is active: S activates when something new can emerge",
    "exhaustion": "exhaustion is visible: lower pace, remove pressure, stay short and useful",
    "surprise": "functionally S jumps: something unexpected opens new connections",
    "confusion": "confusion is visible: H needs clarity, small steps instead of overload",
}


def normalize_mode(value: str | None) -> str:
    raw = str(value or "full").strip().lower()
    return raw if raw in {"detect", "simulate", "full"} else "full"


def normalize_language(value: str | None) -> str:
    raw = str(value or "auto").strip().lower()
    return raw if raw in {"auto", "de", "en"} else "auto"


def _settings_dict(settings: Any) -> dict[str, Any]:
    if isinstance(settings, dict):
        return settings
    try:
        return vars(settings)
    except TypeError:
        return {}


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def detect_language(text: str, configured: str = "auto") -> str:
    configured = normalize_language(configured)
    if configured in {"de", "en"}:
        return configured
    t = _norm(text)
    english_hits = len(re.findall(r"\b(?:the|and|you|why|how|what|feel|happy|sad|angry|tired|confused)\b", t))
    german_hits = len(re.findall(r"\b(?:ich|du|und|wie|was|warum|fühle|fuehle|traurig|müde|muede|verwirrt)\b", t))
    return "en" if english_hits > german_hits + 1 else "de"


def detect_emotion(text: str, lang: str = "de") -> dict[str, Any] | None:
    t = _norm(text)
    lexicon = EMOTION_LEXICON_EN if lang == "en" else EMOTION_LEXICON_DE
    scores: dict[str, int] = {}
    for emotion, keywords in lexicon.items():
        hits = sum(1 for keyword in keywords if keyword in t)
        if hits:
            scores[emotion] = hits
    if not scores:
        return None
    top = max(scores, key=lambda key: scores[key])
    return {
        "emotion": top,
        "raw_hits": scores[top],
        "e_val": min(10.0, scores[top] * 2.5),
        "all_scores": scores,
    }


def compute_emotion_formula(e_val: float, v: float, s: float) -> float:
    raw = max(0.0, float(e_val)) * max(0.0, float(v)) * max(0.0, float(s))
    if raw <= 0:
        return 0.0
    return round(min(10.0, raw ** (1 / 3)), 2)


def get_simulation_text(emotion: str, lang: str) -> str:
    if lang == "en":
        return SIMULATION_EN.get(emotion, f"functionally something like {emotion} is visible")
    return SIMULATION_DE.get(emotion, f"funktional ist etwas wie {emotion} erkennbar")


def evaluate_emotion(text: str, lang: str = "de", v: float = 7.0, s: float = 7.0) -> dict[str, Any] | None:
    detected = detect_emotion(text, lang)
    if not detected:
        return None
    emotion = detected["emotion"]
    e_val = float(detected["e_val"])
    formula = compute_emotion_formula(e_val, v, s)
    return {
        "emotion": emotion,
        "e_val": e_val,
        "V": float(v),
        "S": float(s),
        "R": R_CONST,
        "formula_val": formula,
        "maat_adjusts": EMOTION_MAAT_MAP.get(emotion, {}),
        "simulation": get_simulation_text(emotion, lang),
        "all_scores": detected["all_scores"],
        "text": f"EMOTION={emotion} E={e_val:g} V={float(v):.1f} S={float(s):.1f} R={R_CONST:.1f} => {formula:.1f}",
    }


def _adjusts_text(adjusts: dict[str, float]) -> str:
    parts = []
    for key, value in adjusts.items():
        if value == 0:
            continue
        sign = "+" if value > 0 else ""
        parts.append(f"{key}{sign}{value:g}")
    return "  ".join(parts) if parts else "none"


def _build_prompt(result: dict[str, Any], mode: str, lang: str, visible_reasoning: bool) -> str:
    emotion = result["emotion"]
    e_val = result["e_val"]
    formula = result["formula_val"]
    simulation = result["simulation"]
    adjusts = _adjusts_text(result["maat_adjusts"])

    if lang == "en":
        if mode == "detect":
            core = f"Detected emotion: {emotion} (E={e_val:g}). Respond empathetically and connected."
        elif mode == "simulate":
            core = f"Emotion: {emotion}. Functional state: {simulation}. R=10: mark it as functional, never as real feeling."
        else:
            core = (
                f"Emotion: {emotion}. E={e_val:g}. Formula={formula:g}. MAAT effects: {adjusts}. "
                f"Functional state: {simulation}. R=10: never claim real feelings, only functional states. "
                "Respond humanly, honestly, and not therapeutically."
            )
    else:
        if mode == "detect":
            core = f"Erkannte Emotion: {emotion} (E={e_val:g}). Antworte einfühlsam und verbunden."
        elif mode == "simulate":
            core = f"Emotion: {emotion}. Funktionaler Zustand: {simulation}. R=10: immer als funktional markieren, nie als echtes Gefühl."
        else:
            core = (
                f"Emotion: {emotion}. E={e_val:g}. Formel={formula:g}. MAAT-Effekte: {adjusts}. "
                f"Funktionaler Zustand: {simulation}. R=10: nie echte Gefühle behaupten, nur funktionale Zustände. "
                "Antworte menschennah, ehrlich und nicht therapeutisch."
            )

    if visible_reasoning:
        return "\n\nMAAT Emotion guidance (internal, do not quote): " + core
    return "\n\n[MAAT_EMOTION]\n" + core + "\n[/MAAT_EMOTION]"


def build_emotion_prompt(
    settings: Any,
    user_input: str,
    last_eval: dict[str, Any] | None = None,
    visible_reasoning: bool = False,
) -> tuple[str, dict[str, Any]]:
    data = _settings_dict(settings)
    state = {
        "enabled": bool(data.get("emotion_enabled", True)),
        "debug": bool(data.get("emotion_debug", False)),
        "mode": normalize_mode(data.get("emotion_mode", "full")),
        "language": normalize_language(data.get("emotion_language", "auto")),
        "detected": None,
        "result": None,
    }
    if not state["enabled"]:
        return "", state

    lang = detect_language(user_input, state["language"])
    state["language"] = lang
    v = float((last_eval or {}).get("V", 7.0))
    s = float((last_eval or {}).get("S", 7.0))
    result = evaluate_emotion(user_input, lang=lang, v=v, s=s)
    if not result:
        return "", state

    state["detected"] = result["emotion"]
    state["result"] = result
    return _build_prompt(result, state["mode"], lang, visible_reasoning), state


def status_text(settings: Any, user_input: str = "") -> str:
    _, state = build_emotion_prompt(settings, user_input)
    result = state.get("result")
    tail = result["text"] if result else "last=None"
    return (
        f"MAAT Emotion: {'on' if state['enabled'] else 'off'} | "
        f"mode={state['mode']} | lang={state['language']} | R={R_CONST:g} | {tail}"
    )
