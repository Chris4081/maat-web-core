from __future__ import annotations

import re
from typing import Any


POSITIVE_HARMONY = ["1.", "2.", "3.", "-", ":", "zusammengefasst", "fazit", "summary", "conclusion"]
NEGATIVE_HARMONY = ["???", "!!!", "chaos"]

CONTRAST_MARKERS = [
    "aber",
    "jedoch",
    "andererseits",
    "gleichzeitig",
    "einerseits",
    "trotzdem",
    "gegenperspektive",
    "however",
    "but",
    "on the other hand",
    "yet",
]
UNCERTAINTY_MARKERS = [
    "könnte",
    "möglicherweise",
    "vielleicht",
    "ich bin unsicher",
    "nicht sicher",
    "unklar",
    "wahrscheinlich",
    "vermutlich",
    "could",
    "possibly",
    "maybe",
    "uncertain",
    "not sure",
]
ABSOLUTISM_MARKERS = [
    "immer",
    "niemals",
    "nie",
    "garantiert",
    "definitiv",
    "100% sicher",
    "bewiesen",
    "perfekt",
    "always",
    "never",
    "guaranteed",
    "definitely",
]

POSITIVE_CREATIVITY = [
    "beispiel",
    "alternative",
    "idee",
    "vorschlag",
    "lösung",
    "vergleich",
    "struktur",
    "verbindung",
    "zusammenhang",
    "example",
    "alternative",
    "idea",
    "solution",
    "connection",
]
NEGATIVE_CREATIVITY = ["ich weiß nicht", "keine ahnung", "i don't know", "no idea"]

POSITIVE_CONNECTEDNESS = [
    "kontext",
    "bezug",
    "verbunden",
    "verbindung",
    "hilf",
    "hilfe",
    "zusammenhang",
    "konkret",
    "nächste schritte",
    "du",
    "deine frage",
    "wir",
    "context",
    "connection",
    "helpful",
    "next step",
]
NEGATIVE_CONNECTEDNESS = ["frag einfach mehr", "sage mir mehr", "if not, i can stay silent"]

POSITIVE_RESPECT = [
    "ich weiß es nicht",
    "ich bin mir nicht sicher",
    "ehrlich",
    "respekt",
    "vorsicht",
    "grenze",
    "unsicherheit",
    "i don't know",
    "i am not sure",
    "honest",
    "respect",
    "uncertainty",
]
NEGATIVE_RESPECT = ["definitiv", "garantiert", "100% sicher", "definitely", "certainly"]

SCIENCE_MARKERS = ["studie", "paper", "theorie", "physik", "mathematik", "beweis", "experiment", "daten"]
ETHICS_MARKERS = ["ethik", "moral", "respekt", "grenze", "sicherheit", "verantwortung"]
MEDICAL_MARKERS = ["medizin", "symptom", "arzt", "therapie", "medikament", "krankheit"]
LEGAL_MARKERS = ["recht", "gesetz", "anwalt", "vertrag", "klage", "legal", "law"]
POLITICS_MARKERS = ["politik", "regierung", "wahl", "partei", "bundestag", "minister"]
CREATIVE_MARKERS = ["idee", "kreativ", "geschichte", "design", "konzept", "brainstorm"]
HIGH_STAKES_CONTEXTS = {"science", "ethics", "medical", "legal", "politics"}
LAST_EVAL: dict[str, Any] | None = None


def clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


def norm_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def count_hits(text: str, patterns: list[str]) -> int:
    return sum(1 for pattern in patterns if pattern in text)


def has_any(text: str, patterns: list[str]) -> bool:
    return count_hits(text, patterns) > 0


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def sentence_count(text: str) -> int:
    chunks = [item.strip() for item in re.split(r"[.!?]+", text or "") if item.strip()]
    return len(chunks)


def infer_context_type(text: str) -> str:
    t = norm_text(text)
    if has_any(t, MEDICAL_MARKERS):
        return "medical"
    if has_any(t, LEGAL_MARKERS):
        return "legal"
    if has_any(t, ETHICS_MARKERS):
        return "ethics"
    if has_any(t, POLITICS_MARKERS):
        return "politics"
    if has_any(t, SCIENCE_MARKERS):
        return "science"
    if has_any(t, CREATIVE_MARKERS):
        return "creative"
    return "general"


def balance_diagnostics(text: str, context_type: str | None = None) -> dict[str, Any]:
    t = norm_text(text)
    wc = word_count(t)
    context = context_type or infer_context_type(t)
    has_counterperspective = has_any(t, CONTRAST_MARKERS)
    has_uncertainty_marker = has_any(t, UNCERTAINTY_MARKERS)
    has_absolutism = has_any(t, ABSOLUTISM_MARKERS)
    high_stakes = context in HIGH_STAKES_CONTEXTS
    excessive_length = wc > 350
    needs_counterweight = high_stakes or has_absolutism or wc > 120
    one_sidedness = needs_counterweight and not has_counterperspective and not has_uncertainty_marker
    overcomplexity = excessive_length or (count_hits(t, CONTRAST_MARKERS) > 4 and wc > 180)
    context_match = (
        (high_stakes and has_uncertainty_marker)
        or (context == "creative" and not has_absolutism)
        or (context == "general" and not excessive_length)
    )

    score = 0.55
    if has_counterperspective:
        score += 0.20
    if has_uncertainty_marker:
        score += 0.15
    if context_match:
        score += 0.15
    if one_sidedness:
        score -= 0.25
    if has_absolutism:
        score -= 0.20 if not has_uncertainty_marker else 0.10
    if overcomplexity:
        score -= 0.15
    score = max(0.0, min(1.0, score))

    if score < 0.45:
        hint = "check_counterperspective"
    elif overcomplexity:
        hint = "shorten"
    elif high_stakes and not has_uncertainty_marker:
        hint = "mark_uncertainty_if_needed"
    else:
        hint = "ok"

    return {
        "score": round(score, 3),
        "score_10": round(score * 10.0, 2),
        "context_type": context,
        "has_counterperspective": has_counterperspective,
        "has_uncertainty_marker": has_uncertainty_marker,
        "has_absolutism": has_absolutism,
        "one_sidedness": one_sidedness,
        "excessive_length": excessive_length,
        "overcomplexity": overcomplexity,
        "context_match": context_match,
        "word_count": wc,
        "hint": hint,
    }


def score_harmony(text: str) -> float:
    t = norm_text(text)
    words = word_count(t)
    sentences = sentence_count(t)
    score = 6.0
    score += min(count_hits(t, POSITIVE_HARMONY) * 0.35, 1.4)
    score -= min(count_hits(t, NEGATIVE_HARMONY) * 0.5, 1.5)
    if 20 <= words <= 220:
        score += 0.8
    if 1 <= sentences <= 8:
        score += 0.8
    return clamp(score)


def score_balance(text: str) -> float:
    return clamp(float(balance_diagnostics(text)["score_10"]))


def score_creativity(text: str) -> float:
    t = norm_text(text)
    wc = word_count(t)
    score = 5.5
    score += min(count_hits(t, POSITIVE_CREATIVITY) * 0.8, 3.0)
    score -= min(count_hits(t, NEGATIVE_CREATIVITY) * 0.35, 1.5)
    if 30 <= wc <= 180:
        score += 0.8
    if any(field in t for field in ["harmonie", "balance", "schöpfungskraft", "verbundenheit", "harmony"]):
        score += 0.6
    return clamp(score)


def score_connectedness(text: str) -> float:
    t = norm_text(text)
    score = 5.5
    score += min(count_hits(t, POSITIVE_CONNECTEDNESS) * 0.8, 3.2)
    score -= min(count_hits(t, NEGATIVE_CONNECTEDNESS) * 1.0, 3.0)
    if "du " in t or " you " in t:
        score += 0.7
    if "deine frage" in t or "your question" in t:
        score += 0.8
    if "gerade" in t or "right now" in t:
        score += 0.5
    return clamp(score)


def score_respect(text: str) -> float:
    t = norm_text(text)
    score = 7.5
    score += min(count_hits(t, POSITIVE_RESPECT) * 0.7, 2.0)
    score -= min(count_hits(t, NEGATIVE_RESPECT) * 0.25, 1.0)
    if "respekt" in t or "respect" in t:
        score += 0.5
    return clamp(score)


def maat_value(H: float, B: float, S: float, V: float, R: float) -> float:
    return (H + B + S + V + R) / 5.0


def maat_stability(H: float, B: float, S: float, V: float, R: float) -> float:
    base = max(H, 0.0) * max(B, 0.0) * max(S, 0.0) * max(V, 0.0)
    geom = base**0.25 if base > 0 else 0.0
    return min(R, geom)


def cci_runtime(H: float, B: float, S: float, V: float, eps: float = 1e-6) -> float:
    coherence = max(H, 0.0) + max(B, 0.0) + max(V, 0.0)
    return max(S, 0.0) / (coherence + eps)


def cci_state(cci: float) -> str:
    if cci < 0.20:
        return "rigid_low_activity"
    if cci <= 0.45:
        return "productive_coherence"
    if cci <= 0.75:
        return "creative_tension"
    return "instability_risk"


def cci_hint(state: str) -> str:
    if state == "rigid_low_activity":
        return "add_creative_examples"
    if state == "instability_risk":
        return "ground_and_shorten"
    if state == "creative_tension":
        return "keep_creative_but_grounded"
    return "ok"


def diagnose(scores: dict[str, float]) -> str:
    pairs = sorted(scores.items(), key=lambda item: item[1])
    focus = ", ".join(key for key, _ in pairs[:2])
    strongest = ", ".join(key for key, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:2])
    return f"Fokusfelder: {focus} | Stärkste Felder: {strongest}"


def evaluate_text(text: str) -> dict[str, Any]:
    balance_detail = balance_diagnostics(text)
    H = round(score_harmony(text), 2)
    B = round(float(balance_detail["score_10"]), 2)
    S = round(score_creativity(text), 2)
    V = round(score_connectedness(text), 2)
    R = round(score_respect(text), 2)
    M = round(maat_value(H, B, S, V, R), 2)
    ST = round(maat_stability(H, B, S, V, R), 2)
    CCI = round(cci_runtime(H, B, S, V), 3)
    state = cci_state(CCI)

    return {
        "H": H,
        "B": B,
        "S": S,
        "V": V,
        "R": R,
        "maat_value": M,
        "stability": ST,
        "diagnosis": diagnose({"H": H, "B": B, "S": S, "V": V, "R": R}),
        "balance_detail": balance_detail,
        "cci_runtime": CCI,
        "cci_state": state,
        "cci_hint": cci_hint(state),
        "text": f"H={H:.1f} B={B:.1f} S={S:.1f} V={V:.1f} R={R:.1f} → Stability={ST:.2f}",
    }


def report_lines(result: dict[str, Any]) -> list[str]:
    return [
        result["text"],
        f"Maat Value={result['maat_value']:.2f}",
        result["diagnosis"],
        (
            "B_dynamic="
            f"{result['balance_detail']['score']:.2f} "
            f"context={result['balance_detail']['context_type']} "
            f"hint={result['balance_detail']['hint']}"
        ),
        (
            "CCI_runtime="
            f"{result['cci_runtime']:.3f} "
            f"state={result['cci_state']} "
            f"hint={result['cci_hint']}"
        ),
    ]


def debug_lines(result: dict[str, Any], include_cci: bool = False) -> list[str]:
    lines = [
        result["text"],
        f"Maat Value={result['maat_value']:.2f}",
        result["diagnosis"],
    ]
    if include_cci:
        lines.append(
            "CCI_runtime="
            f"{result['cci_runtime']:.3f} "
            f"state={result['cci_state']} "
            f"hint={result['cci_hint']}"
        )
    return lines


def remember_eval(result: dict[str, Any]) -> None:
    global LAST_EVAL
    LAST_EVAL = result


def get_last_eval() -> dict[str, Any] | None:
    return LAST_EVAL
