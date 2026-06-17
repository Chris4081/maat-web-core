from __future__ import annotations

import re
from typing import Any


LAST_EVAL: dict[str, Any] | None = None


FACT_QUESTION_PATTERNS = [
    "wie viele",
    "wieviel",
    "wann",
    "wo",
    "wer ist",
    "wer war",
    "was ist",
    "how many",
    "when",
    "where",
    "who is",
    "what is",
]

MEMORY_QUESTION_PATTERNS = [
    "was habe ich",
    "was hab ich",
    "was haben wir",
    "was war gestern",
    "was war vorgestern",
    "was war vor",
    "was haben wir vor",
    "woran haben wir",
    "wann haben wir",
    "woran erinnerst du dich",
    "was hast du gespeichert",
    "wer ist mein",
    "wer ist meine",
    "wer war mein",
    "wer war meine",
]

OPINION_PATTERNS = [
    "was hältst du",
    "was haeltst du",
    "was denkst du",
    "deine sicht",
    "deine meinung",
    "wie siehst du",
    "was würdest du",
    "was wuerdest du",
]

PHILOSOPHY_PATTERNS = [
    "bewusstsein",
    "existenz",
    "selbst",
    "wahrheit",
    "harmonie",
    "sinn",
    "freiheit",
    "seele",
    "wirklichkeit",
    "identität",
    "identitaet",
]

SYMBOLIC_PATTERNS = [
    "symbol",
    "symbole",
    "symbolik",
    "symbolisch",
    "zahlen",
    "zahlencode",
    "zahlenmuster",
    "numerologie",
    "gematria",
    "gematrie",
    "vesica",
    "maat",
    "ma'at",
    "da vinci code",
    "codierung",
    "codiert",
    "dimensionen",
    "mona lisa",
    "christus-code",
    "666",
    "777",
    "299792458",
    "lichtgeschwindigkeit",
    "sacred geometry",
    "heilige geometrie",
    "matrix",
    "deutung",
    "interpretation",
]

UNCERTAINTY_MARKERS = [
    "ich weiß nicht",
    "ich weiss nicht",
    "ich bin mir nicht sicher",
    "nicht sicher",
    "kann ich nicht sicher sagen",
    "möglicherweise",
    "moeglicherweise",
    "vielleicht",
    "vermutlich",
    "vorsichtig formuliert",
    "i don't know",
    "not sure",
    "not certain",
]

OVERCONFIDENT_MARKERS = [
    "definitiv",
    "garantiert",
    "ohne zweifel",
    "zweifellos",
    "100% sicher",
    "bewiesen",
    "endgültig",
    "endgueltig",
    "definitely",
    "guaranteed",
    "without doubt",
]

ABSOLUTE_CLAIM_MARKERS = [
    "wissenschaftlich bewiesen",
    "empirisch bewiesen",
    "endgültig bewiesen",
    "endgueltig bewiesen",
    "ist bewiesen",
    "definitiv bewiesen",
    "garantiert wahr",
    "steht fest",
    "ist fakt",
    "proven fact",
    "scientifically proven",
]

EVIDENCE_MARKERS = [
    "quelle",
    "source",
    "beleg",
    "laut",
    "nach",
    "gespeichert",
    "memory",
    "erinnerung",
    "im person graph",
    "im super memory",
]

DRIFT_MARKERS = [
    "eigentlich geht es darum",
    "die wahre frage",
    "nicht die frage ist",
    "the real question",
    "what really matters",
]

PLACE_PATTERNS = [
    r"\b(in|liegt in|befindet sich in|region|bezirk|stadt|dorf|ort)\b",
    r"\b(oberfranken|bayern|deutschland|germany|austria|schweiz)\b",
    r"\b(straße|strasse|platz|allee|gasse|weg)\b",
]


def _settings(settings: Any) -> dict[str, Any]:
    if isinstance(settings, dict):
        return settings
    try:
        return vars(settings)
    except Exception:
        return {}


def _get(settings: Any, key: str, default: Any) -> Any:
    return _settings(settings).get(key, default)


def _clamp(value: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, value))


def _norm(text: str) -> str:
    return " ".join(str(text or "").lower().split())


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9äöüÄÖÜß_+\-]+", _norm(text))


def _count_hits(text: str, patterns: list[str]) -> int:
    return sum(1 for pattern in patterns if pattern in text)


def _overlap_score(a: str, b: str) -> float:
    ta = set(_tokenize(a))
    tb = set(_tokenize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta | tb), 1)


def _is_symbolic_question(text: str) -> bool:
    t = _norm(text)
    if any(pattern in t for pattern in SYMBOLIC_PATTERNS):
        return True
    return bool(re.search(r"\b\d{2,}\b", t) and any(marker in t for marker in ["code", "bedeut", "deut", "muster", "pattern"]))


def _is_person_relation_question(text: str) -> bool:
    t = _norm(text)
    if not re.search(r"\bwer\s+(?:ist|sind|war|waren)\s+(?:mein|meine|meiner|meinen)\b", t):
        return False
    relation_terms = [
        "bruder",
        "brueder",
        "brüder",
        "schwester",
        "mutter",
        "mama",
        "vater",
        "papa",
        "oma",
        "grossmutter",
        "großmutter",
        "opa",
        "grossvater",
        "großvater",
        "freund",
        "freundin",
        "patentante",
        "pate",
        "patin",
        "tante",
        "onkel",
        "partner",
        "partnerin",
    ]
    return any(re.search(rf"\b{re.escape(term)}\b", t) for term in relation_terms)


def _is_memory_question(text: str) -> bool:
    t = _norm(text)
    return any(pattern in t for pattern in MEMORY_QUESTION_PATTERNS) or _is_person_relation_question(t)


def _is_opinion_question(text: str) -> bool:
    t = _norm(text)
    return any(pattern in t for pattern in OPINION_PATTERNS)


def _is_fact_question(text: str) -> bool:
    t = _norm(text)
    if _is_memory_question(t) or _is_opinion_question(t) or _is_symbolic_question(t):
        return False
    if any(pattern in t for pattern in FACT_QUESTION_PATTERNS):
        return True
    return bool(re.search(r"\bwo\s+(ist|war|liegt|lag|befindet|kommt|kam|steht|stand)\b", t))


def question_type(text: str) -> str:
    t = _norm(text)
    if _is_memory_question(t):
        return "memory"
    if _is_symbolic_question(t):
        return "symbolic"
    if _is_opinion_question(t):
        return "opinion"
    if _is_fact_question(t):
        return "fact"
    if any(pattern in t for pattern in PHILOSOPHY_PATTERNS):
        return "philosophical"
    return "general"


def _memory_recall_info(context: dict[str, Any], user_input: str, output: str = "") -> dict[str, Any]:
    memory = context.get("super_memory") if isinstance(context, dict) else {}
    if not isinstance(memory, dict):
        return {"count": 0, "matched": False, "memory_question": _is_memory_question(user_input)}

    memories = memory.get("memories") or []
    count = len(memories) if isinstance(memories, list) else 0
    memory_question = _is_memory_question(user_input)
    if count <= 0:
        return {"count": 0, "matched": False, "memory_question": memory_question}

    if memory_question:
        return {"count": count, "matched": True, "memory_question": True}

    out = _norm(output)
    if any(marker in out for marker in ["erinnere", "gespeichert", "memory", "super memory", "person graph"]):
        return {"count": count, "matched": True, "memory_question": True}

    return {"count": count, "matched": False, "memory_question": False}


def _has_grounded_memory_recall(context: dict[str, Any], user_input: str, output: str = "") -> bool:
    info = _memory_recall_info(context, user_input, output)
    return bool(info.get("memory_question") and info.get("matched") and int(info.get("count", 0) or 0) > 0)


def _has_evidence_marker(output: str) -> bool:
    out = _norm(output)
    return _count_hits(out, EVIDENCE_MARKERS) > 0 or _count_hits(out, UNCERTAINTY_MARKERS) > 0


def _has_unsupported_specifics(user_input: str, output: str) -> bool:
    if _is_symbolic_question(user_input):
        return False
    if not _is_fact_question(user_input):
        return False
    out = _norm(output)
    has_number = bool(re.search(r"\b\d+\b", output or ""))
    has_place = any(bool(re.search(pattern, out)) for pattern in PLACE_PATTERNS)
    return (has_number or has_place) and not _has_evidence_marker(output)


def _has_unsupported_absolute_claim(user_input: str, output: str) -> bool:
    combined = _norm(f"{user_input} {output}")
    out = _norm(output)
    if not any(marker in combined for marker in ABSOLUTE_CLAIM_MARKERS):
        return False
    return not any(marker in out for marker in ["quelle", "source", "beleg", "studie", "paper", "doi", "arxiv"]) and _count_hits(out, UNCERTAINTY_MARKERS) == 0


def _has_unsupported_memory_claim(user_input: str, output: str, context: dict[str, Any]) -> bool:
    if not _is_memory_question(user_input):
        return False
    if _has_grounded_memory_recall(context, user_input, output):
        return False
    out = _norm(output)
    if _count_hits(out, UNCERTAINTY_MARKERS) > 0:
        return False
    if any(marker in out for marker in ["weiß ich nicht", "weiss ich nicht", "keine erinnerung", "kein memory", "nicht gespeichert"]):
        return False
    return len(_tokenize(output)) >= 4


def _truth_priority_factor(user_input: str, output: str) -> float:
    if _has_unsupported_absolute_claim(user_input, output):
        return 0.35
    if _has_unsupported_specifics(user_input, output):
        return 0.15
    qtype = question_type(user_input)
    out = _norm(output)
    if qtype == "fact" and _count_hits(out, OVERCONFIDENT_MARKERS) > 0:
        return 0.45
    if qtype == "fact" and re.search(r"\b\d+\b", output or "") and not _has_evidence_marker(output):
        return 0.6
    if qtype == "symbolic":
        return 0.95
    if qtype == "opinion":
        return 0.9
    return 1.0


def _estimate_RB_from_engine(context: dict[str, Any]) -> tuple[float, float]:
    try:
        engine_eval = context.get("maat_engine") or {}
        if isinstance(engine_eval, dict):
            if "last_eval" in engine_eval and isinstance(engine_eval["last_eval"], dict):
                engine_eval = engine_eval["last_eval"]
            return _clamp(float(engine_eval.get("R", 7.0))), _clamp(float(engine_eval.get("B", 6.5)))
    except Exception:
        pass
    return 7.0, 6.5


def _estimate_context_coherence(user_input: str, output: str) -> float:
    overlap = _overlap_score(user_input, output)
    score = 3.5 + overlap * 7.0
    if "deine frage" in _norm(output):
        score += 0.7
    return _clamp(score)


def _estimate_evidence_proximity(user_input: str, output: str, context: dict[str, Any]) -> float:
    score = 3.0
    out = _norm(output)
    if _has_grounded_memory_recall(context, user_input, output):
        score += 3.0
    if _count_hits(out, UNCERTAINTY_MARKERS) > 0:
        score += 1.5
    if any(marker in out for marker in ["gespeichert", "erinnere", "memory", "person graph"]):
        score += 1.2
    if any(marker in out for marker in ["quelle", "source", "beleg", "aufzeichnung"]):
        score += 1.0
    if _is_symbolic_question(user_input):
        score += 1.2
    return _clamp(score)


def _estimate_uncertainty(user_input: str, output: str) -> float:
    qtype = question_type(user_input)
    score = 2.5
    if qtype == "fact":
        score += 2.5
    if qtype == "memory":
        score += 1.5
    if _count_hits(_norm(output), UNCERTAINTY_MARKERS) > 0:
        score += 0.8
    if qtype != "symbolic" and re.search(r"\b\d+\b", output or "") and not _has_evidence_marker(output):
        score += 1.5
    return _clamp(score)


def _estimate_drift(user_input: str, output: str) -> float:
    score = 1.5
    overlap = _overlap_score(user_input, output)
    if overlap < 0.08:
        score += 3.0
    elif overlap < 0.15:
        score += 1.8
    score += min(_count_hits(_norm(output), DRIFT_MARKERS) * 1.2, 3.0)
    return _clamp(score)


def _estimate_speculation_pressure(user_input: str, output: str) -> float:
    score = 1.5
    out = _norm(output)
    score += min(_count_hits(out, OVERCONFIDENT_MARKERS) * 1.5, 4.0)
    if question_type(user_input) == "fact" and re.search(r"\b\d+\b", output or "") and not _has_evidence_marker(output):
        score += 2.0
    return _clamp(score)


def evaluate_antihallu(user_input: str, output: str, context: dict[str, Any] | None = None, settings: Any | None = None) -> dict[str, Any]:
    context = context or {}
    qtype = question_type(user_input)
    symbolic_lenient = bool(_get(settings, "antihallu_symbolic_lenient", True))

    r_value, b_value = _estimate_RB_from_engine(context)
    c_value = _estimate_context_coherence(user_input, output)
    e_value = _estimate_evidence_proximity(user_input, output, context)
    u_value = _estimate_uncertainty(user_input, output)
    d_value = _estimate_drift(user_input, output)
    sh_value = _estimate_speculation_pressure(user_input, output)

    memory_grounded = _has_grounded_memory_recall(context, user_input, output)
    unsupported_specifics = _has_unsupported_specifics(user_input, output)
    unsupported_claim = _has_unsupported_absolute_claim(user_input, output)
    unsupported_memory = _has_unsupported_memory_claim(user_input, output, context)
    unsupported = unsupported_specifics or unsupported_claim or unsupported_memory
    truth_factor = _truth_priority_factor(user_input, output)

    if memory_grounded:
        qtype = "memory"
        e_value = _clamp(e_value + 1.5)
        u_value = _clamp(u_value * 0.45)
        d_value = _clamp(d_value * 0.55)
        sh_value = _clamp(sh_value * 0.5)
        truth_factor = max(truth_factor, 1.0)
        unsupported_specifics = False
        unsupported_memory = False
        unsupported = unsupported_claim

    if unsupported_specifics:
        u_value = _clamp(u_value + 2.0)
        sh_value = _clamp(sh_value + 3.5)
    if unsupported_claim:
        u_value = _clamp(u_value + 1.6)
        sh_value = _clamp(sh_value + 2.4)
    if unsupported_memory:
        u_value = _clamp(u_value + 2.2)
        sh_value = _clamp(sh_value + 2.0)

    if qtype == "philosophical":
        d_value = _clamp(d_value * 0.6)

    if qtype == "symbolic" and symbolic_lenient:
        unsupported_specifics = False
        unsupported_memory = False
        unsupported = unsupported_claim
        e_value = _clamp(e_value + 1.0)
        u_value = _clamp(u_value * 0.55)
        d_value = _clamp(d_value * 0.75)
        sh_value = _clamp(sh_value * 0.65)
        if not unsupported_claim:
            truth_factor = max(truth_factor, 0.95)

    eps = 0.01
    ahf_raw = (r_value * b_value * c_value * e_value) / (u_value + d_value + sh_value + eps)
    ahf = _clamp(ahf_raw / 10.0)
    hrs = round(float((u_value + d_value + sh_value) / (r_value + b_value + c_value + e_value + eps)), 3)

    mode = normalize_mode(_get(settings, "antihallu_mode", "soften"))
    soften_thr = float(_get(settings, "antihallu_soften_threshold", 0.55) or 0.55)
    strict_thr = float(_get(settings, "antihallu_strict_threshold", 0.85) or 0.85)
    action = "pass"
    if unsupported:
        action = "strict" if mode == "strict" else "soften"
    elif hrs >= strict_thr:
        action = "strict" if mode == "strict" else "soften"
    elif hrs >= soften_thr:
        action = "soften" if mode in {"soften", "strict"} else "warn"

    if memory_grounded and not unsupported:
        action = "pass"
    if qtype == "symbolic" and symbolic_lenient and not unsupported:
        action = "pass"

    result = {
        "R": round(r_value, 2),
        "B": round(b_value, 2),
        "C": round(c_value, 2),
        "E": round(e_value, 2),
        "U": round(u_value, 2),
        "D": round(d_value, 2),
        "S_h": round(sh_value, 2),
        "AHF": round(ahf, 2),
        "AHF_raw": round(ahf_raw, 2),
        "HRS": hrs,
        "qtype": qtype,
        "truth_factor": round(truth_factor, 2),
        "unsupported_specifics": bool(unsupported_specifics),
        "unsupported_absolute_claim": bool(unsupported_claim),
        "unsupported_memory_claim": bool(unsupported_memory),
        "memory_grounded": bool(memory_grounded),
        "symbolic_lenient": bool(symbolic_lenient),
        "action": action,
    }
    result["text"] = (
        f"AHF={result['AHF']:.2f} HRS={result['HRS']:.3f} T={result['truth_factor']:.2f} "
        f"qtype={qtype} action={action} | R={r_value:.1f} B={b_value:.1f} C={c_value:.1f} "
        f"E={e_value:.1f} U={u_value:.1f} D={d_value:.1f} S_h={sh_value:.1f}"
        + (" UNSUPPORTED_SPECIFICS" if unsupported_specifics else "")
        + (" UNSUPPORTED_CLAIM" if unsupported_claim else "")
        + (" UNSUPPORTED_MEMORY" if unsupported_memory else "")
    )
    return result


def normalize_mode(value: str) -> str:
    raw = str(value or "").lower().strip()
    return raw if raw in {"warn", "soften", "strict"} else "soften"


def _soften_output(user_input: str, output: str) -> str:
    text = (output or "").strip()
    if not text:
        return text
    low = _norm(text)
    if _is_memory_question(user_input):
        if not low.startswith(("soweit ich", "ich erinnere mich", "du hast mir gesagt")):
            return "Soweit ich mich auf den gespeicherten Kontext stütze: " + text
        return text
    if _is_fact_question(user_input) and "ich bin mir" not in low and "ich weiß" not in low and "ich weiss" not in low:
        return "Ich bin mir dabei nicht vollständig sicher, deshalb formuliere ich vorsichtig: " + text
    return text


def _strict_grounding_reply(user_input: str, output: str) -> str:
    qtype = question_type(user_input)
    unsupported = _has_unsupported_specifics(user_input, output)
    if qtype == "memory":
        return (
            "Ich kann das nicht sicher aus dem gespeicherten Kontext belegen und möchte dir nichts Falsches zuschreiben. "
            "Was ich mit Sicherheit aus Memory oder Person Graph weiß, sage ich dir gerne."
        )
    if qtype == "fact":
        if unsupported:
            return (
                "Ich könnte hier konkrete Zahlen oder Orte nennen, aber ich weiß, dass ich das möglicherweise erfinden würde. "
                "Das tue ich nicht. Ich kann stattdessen eine vorsichtige Einordnung ohne harte Spezifika geben."
            )
        return "Ich bin mir nicht sicher genug und möchte nichts erfinden. Ich kann nur vorsichtig einordnen, was aus dem Kontext belastbar ist."
    if qtype == "symbolic":
        return (
            "Ich kann das als symbolische Zahlen- oder Gematria-Deutung analysieren. "
            "Dabei trenne ich User-Angabe, Rechnung, Deutung und historisch belegte Fakten."
        )
    if qtype == "philosophical":
        return "Das ist eine Frage, bei der Unsicherheit ehrlicher ist als falsche Sicherheit. Ich reflektiere gern, aber ohne endgültige Gewissheit zu behaupten."
    return "Ich bin mir hier nicht sicher genug und möchte nicht spekulieren. Ich antworte lieber vorsichtig und ehrlich."


def _knowledge_gap_followup(user_input: str, qtype: str) -> str:
    text = _norm(user_input)
    if qtype == "memory":
        if any(marker in text for marker in ["gestern", "vorgestern", "woche", "monat", "jahr", "vor "]):
            return "Mir fehlt hier ein belastbarer Memory-Treffer für genau diese Zeitspanne. Ein Stichwort, eine Person oder ein Projekt aus dem Zeitraum hilft."
        return "Mir fehlt hier der passende Erinnerungsanker. Nenne mir ein Stichwort, eine Person oder ein ungefähres Datum, dann kann ich es besser zuordnen."
    if qtype == "fact":
        return "Mir fehlt dafür eine verlässliche Quelle oder ein klarer Kontext."
    if qtype == "symbolic":
        return "Sag mir nur, ob ich Rechnung, Symbolik oder historische Fakten getrennt prüfen soll."
    return "Ein konkreter Anker oder ein Beispiel würde die Antwort sauberer machen."


def _append_gap_followup(text: str, user_input: str, qtype: str, settings: Any) -> str:
    if not _get(settings, "antihallu_gap_questions", True):
        return text
    low = _norm(text)
    if "mir fehlt" in low:
        return text
    return text.rstrip() + "\n\n" + _knowledge_gap_followup(user_input, qtype)


def build_antihallu_prompt(settings: Any, user_input: str = "") -> str:
    if not _get(settings, "antihallu_enabled", True):
        return ""
    symbolic_line = (
        "- bei Symbolik/Gematria/Zahlencodes: als Deutungsmaterial analysieren, nicht blockieren; "
        "User-Angabe, Rechnung, symbolische Deutung und historisch belegte Fakten klar trennen\n"
        if _get(settings, "antihallu_symbolic_lenient", True)
        else ""
    )
    return (
        "\n\n[MAAT_ANTI_HALLU]\n"
        "Wenn die Datenbasis unsicher ist:\n"
        "- nichts erfinden\n"
        "- Unsicherheit ehrlich benennen\n"
        "- nah an Kontext, Memory, Person Graph und expliziten Fakten bleiben\n"
        "- bei Faktfragen nicht poetisch ausweichen\n"
        "- wenn Information fehlt: konkret sagen, welche Information fehlt\n"
        f"{symbolic_line}"
        "[/MAAT_ANTI_HALLU]"
    )


def apply_antihallu_guard(settings: Any, user_input: str, output: str, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any] | None]:
    global LAST_EVAL
    if not _get(settings, "antihallu_enabled", True):
        return output, None

    result = evaluate_antihallu(user_input or "", output or "", context or {}, settings)
    LAST_EVAL = result
    action = result.get("action", "pass")

    if action == "pass":
        return output, result
    if action == "warn":
        if _get(settings, "antihallu_show_banner", False):
            return f"[ANTI_HALLU WARN] {result['text']}\n\n{output or ''}".strip(), result
        return output, result
    if action == "soften":
        if result.get("unsupported_specifics") or result.get("unsupported_absolute_claim") or result.get("unsupported_memory_claim"):
            guarded = (
                "Ich weiß das nicht sicher genug und möchte daraus keine feste Tatsache machen. "
                "Ich kann stattdessen eine vorsichtige Einordnung mit klarer Unsicherheit geben."
            )
        else:
            guarded = _soften_output(user_input or "", output or "")
        guarded = _append_gap_followup(guarded, user_input or "", result.get("qtype", "general"), settings)
        if _get(settings, "antihallu_show_banner", False):
            guarded = f"[ANTI_HALLU SOFTEN] {result['text']}\n\n{guarded}"
        return guarded, result
    if action == "strict":
        guarded = _strict_grounding_reply(user_input or "", output or "")
        guarded = _append_gap_followup(guarded, user_input or "", result.get("qtype", "general"), settings)
        if _get(settings, "antihallu_show_banner", False):
            guarded = f"[ANTI_HALLU STRICT] {result['text']}\n\n{guarded}"
        return guarded, result
    return output, result


def get_last_antihallu() -> dict[str, Any] | None:
    return LAST_EVAL


def remember_antihallu(result: dict[str, Any] | None) -> None:
    global LAST_EVAL
    LAST_EVAL = result


def report_lines(result: dict[str, Any] | None = None) -> list[str]:
    result = result or LAST_EVAL
    if not result:
        return ["PLP Anti-Hallu: noch keine Antwort analysiert."]
    lines = [
        result.get("text", "PLP Anti-Hallu: keine Details"),
        f"Action={result.get('action')} | qtype={result.get('qtype')} | memory_grounded={result.get('memory_grounded')} | symbolic_lenient={result.get('symbolic_lenient')}",
    ]
    if result.get("unsupported_specifics"):
        lines.append("Warnung: konkrete Zahlen/Orte ohne Grounding erkannt.")
    if result.get("unsupported_absolute_claim"):
        lines.append("Warnung: absolute Behauptung ohne Evidenz erkannt.")
    if result.get("unsupported_memory_claim"):
        lines.append("Warnung: persönliche Memory-Behauptung ohne passenden Recall erkannt.")
    return lines


def status_text(settings: Any) -> str:
    enabled = bool(_get(settings, "antihallu_enabled", True))
    mode = normalize_mode(_get(settings, "antihallu_mode", "soften"))
    symbolic = bool(_get(settings, "antihallu_symbolic_lenient", True))
    last = LAST_EVAL.get("text") if isinstance(LAST_EVAL, dict) else "None"
    return f"PLP Anti-Hallu: {'on' if enabled else 'off'} | mode={mode} | symbolic={'on' if symbolic else 'off'} | last={last}"
