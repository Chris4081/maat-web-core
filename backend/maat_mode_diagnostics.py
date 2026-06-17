from __future__ import annotations

from typing import Any

from .maat_balance import balance_state
from .maat_claim_guard import critical_thinking_step
from .maat_emotion import evaluate_emotion, normalize_language as normalize_emotion_language
from .maat_engine import get_last_eval
from .maat_plp_anti_hallu import question_type
from .maat_style import build_style_prompt


DEEP_MARKERS = [
    "jenseits",
    "bewusstsein",
    "existenz",
    "sinn",
    "wer bist du",
    "was bist du",
    "was denkst du",
    "philosophie",
    "wirklich",
    "consciousness",
    "existence",
    "meaning",
    "who are you",
]


def _short(text: str, limit: int = 160) -> str:
    value = " ".join(str(text or "").split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def _dominant_mode(
    user_input: str,
    intent: str,
    tone_vector: dict[str, Any],
    balance_context: str,
    qtype: str,
    emotion: dict[str, Any] | None,
) -> str:
    if intent == "greeting":
        return "social"
    if emotion:
        return "emotion"
    if intent == "technical" or balance_context == "technical":
        return "builder"
    if qtype == "symbolic":
        return "symbolic"
    deep_marker = any(marker in str(user_input or "").lower() for marker in DEEP_MARKERS)
    if intent == "philosophical" or qtype == "philosophical" or balance_context == "philosophical" or deep_marker:
        return "deep"
    if intent == "creative" or balance_context == "creative" or float(tone_vector.get("creative") or 0) >= 0.34:
        return "creative"
    if intent == "analysis":
        return "analysis"
    return "default"


def diagnose_mode(settings: Any, user_input: str) -> dict[str, Any]:
    text = str(user_input or "").strip()
    _, style_info = build_style_prompt(
        settings,
        text,
        visible_reasoning=bool(getattr(settings, "enable_thinking", False)),
    )
    balance_info = balance_state(settings, text, style_info=style_info, last_eval=get_last_eval())
    lang = normalize_emotion_language(getattr(settings, "emotion_language", "auto"))
    emotion_lang = "de" if lang == "auto" else lang
    emotion_info = evaluate_emotion(text, lang=emotion_lang)
    qtype = question_type(text)
    claim_info = critical_thinking_step(text)
    intent = str(style_info.get("intent") or "general")
    tone_vector = style_info.get("tone_vector") if isinstance(style_info.get("tone_vector"), dict) else {}
    balance_context = str(balance_info.get("context_type") or "general")
    mode = _dominant_mode(text, intent, tone_vector, balance_context, qtype, emotion_info)

    return {
        "mode": mode,
        "diagnostic_only": True,
        "input": text,
        "style": {
            "intent": intent,
            "tone": style_info.get("tone_mode"),
            "tone_vector": tone_vector,
            "structure": (style_info.get("rules") or {}).get("structure"),
            "max_words": (style_info.get("rules") or {}).get("max_words"),
        },
        "balance": {
            "context_type": balance_context,
            "skip": bool(balance_info.get("skip")),
            "agreement_pressure": bool(balance_info.get("agreement_pressure")),
        },
        "emotion": {
            "detected": emotion_info.get("emotion") if emotion_info else None,
            "strength": emotion_info.get("e_val") if emotion_info else None,
        },
        "antihallu": {
            "question_type": qtype,
        },
        "claim_guard": {
            "stance": claim_info.get("stance"),
            "risk_level": claim_info.get("risk_level"),
            "needs_challenge": bool(claim_info.get("needs_challenge")),
            "reasons": claim_info.get("reasons") or [],
        },
    }


def report_lines(result: dict[str, Any]) -> list[str]:
    style = result.get("style") or {}
    balance = result.get("balance") or {}
    emotion = result.get("emotion") or {}
    antihallu = result.get("antihallu") or {}
    claim = result.get("claim_guard") or {}
    tone_vector = style.get("tone_vector") or {}
    vector = ", ".join(f"{key}={value}" for key, value in tone_vector.items()) or "-"
    reasons = ", ".join(claim.get("reasons") or []) or "-"
    return [
        f"Mode: {result.get('mode', 'default')} (Diagnose-only, keine Extra-Injection)",
        f"Input: {_short(str(result.get('input') or '')) or '-'}",
        f"Style: intent={style.get('intent')} tone={style.get('tone')} structure={style.get('structure')} max_words={style.get('max_words')}",
        f"Tone vector: {vector}",
        f"Balance: context={balance.get('context_type')} skip={balance.get('skip')} pressure={balance.get('agreement_pressure')}",
        f"Emotion: detected={emotion.get('detected') or '-'} strength={emotion.get('strength') or '-'}",
        f"Anti-Hallu: qtype={antihallu.get('question_type')}",
        f"Claim Guard: stance={claim.get('stance')} risk={claim.get('risk_level')} challenge={claim.get('needs_challenge')} reasons={reasons}",
    ]


def report_markdown(result: dict[str, Any]) -> str:
    return "# MAAT Mode Diagnose\n\n```text\n" + "\n".join(report_lines(result)) + "\n```"
