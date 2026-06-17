from __future__ import annotations

import re
import time
from typing import Any

from .database import Database
from .maat_adaptive_learning import store_lesson


CONTRAST_MARKERS = [
    "aber",
    "jedoch",
    "andererseits",
    "gleichzeitig",
    "trotzdem",
    "gegenperspektive",
    "kritiker",
    "kritik",
    "einschränkung",
    "einschraenkung",
    "abwägung",
    "abwaegung",
    "however",
    "but",
    "on the other hand",
]

UNCERTAINTY_MARKERS = [
    "ich bin unsicher",
    "unsicher",
    "nicht sicher",
    "könnte",
    "koennte",
    "möglicherweise",
    "moeglicherweise",
    "vermutlich",
    "wahrscheinlich",
    "unklar",
    "i am unsure",
    "uncertain",
    "might",
    "could",
    "possibly",
]

ABSOLUTE_MARKERS = [
    "immer",
    "niemals",
    "nie",
    "garantiert",
    "100%",
    "absolut",
    "perfekt",
    "endgültig",
    "endgueltig",
    "bewiesen",
    "unwiderlegbar",
    "ohne zweifel",
    "beste theorie",
    "always",
    "never",
    "guaranteed",
    "perfect",
    "proven",
]

EVIDENCE_MARKERS = [
    "quelle",
    "beleg",
    "daten",
    "messung",
    "empirisch",
    "laut",
    "faktisch",
    "symbolisch",
    "nicht belegt",
    "evidenz",
    "source",
    "evidence",
    "data",
    "measured",
    "according to",
]

CREATIVE_MARKERS = [
    "idee",
    "vorschlag",
    "konzept",
    "modell",
    "architektur",
    "baue",
    "entwickeln",
    "umsetzen",
    "beispiel",
    "option",
    "nächster schritt",
    "naechster schritt",
    "creative",
    "idea",
    "proposal",
    "build",
]

CONNECTION_MARKERS = [
    "du",
    "dir",
    "dein",
    "wir",
    "uns",
    "unser",
    "maat",
    "projekt",
    "memory",
    "erinnerung",
    "kontext",
]

FORMAT_COLLAPSE_PATTERNS = [
    re.compile(r"\S[ \t]+#{1,6}\s+\S"),
    re.compile(r"\S[ \t]+(?:---|\*\*\*|___|⸻)[ \t]+\S"),
    re.compile(r"\S[ \t]+[1-9][0-9]?\.\s+[A-ZÄÖÜ]"),
]

LAST_REPORT: dict[str, Any] | None = None
HISTORY: list[dict[str, Any]] = []


def _norm(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    return parts or [p.strip() for p in str(text or "").splitlines() if p.strip()]


def _has_any(low: str, markers: list[str]) -> bool:
    return any(marker in low for marker in markers)


def _count_any(low: str, markers: list[str]) -> int:
    return sum(1 for marker in markers if marker in low)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _field(value: float) -> float:
    return round(_clamp(value), 3)


def _context_intent(context: dict[str, Any] | None) -> str:
    style = (context or {}).get("maat_style")
    if isinstance(style, dict):
        return str(style.get("intent") or "general")
    return "general"


def _claim_info(context: dict[str, Any] | None) -> dict[str, Any]:
    claim = (context or {}).get("maat_claim_guard")
    return claim if isinstance(claim, dict) else {}


def _paragraph_indexes(paragraphs: list[str], markers: list[str], max_hits: int = 4) -> list[int]:
    hits = []
    for idx, paragraph in enumerate(paragraphs, start=1):
        if _has_any(_norm(paragraph), markers):
            hits.append(idx)
            if len(hits) >= max_hits:
                break
    return hits


def _apply_thresholds(report: dict[str, Any], settings: Any) -> dict[str, Any]:
    scores = report.get("scores", {}) or {}
    warn_b = float(getattr(settings, "feedback_warn_below_b", 0.60) or 0.60)
    warn_r = float(getattr(settings, "feedback_warn_below_r", 0.75) or 0.75)
    warn_h = float(getattr(settings, "feedback_warn_below_h", 0.65) or 0.65)
    intent = str(report.get("intent") or "general")
    simple_intents = {"greeting", "simple_answer", "smalltalk"}
    report["critical"] = (
        float(scores.get("R", 1.0)) < warn_r
        or (intent not in simple_intents and float(scores.get("B", 1.0)) < warn_b)
        or (intent not in {"greeting"} and float(scores.get("H", 1.0)) < warn_h)
    )
    report["thresholds"] = {"B": warn_b, "R": warn_r, "H": warn_h}
    return report


def analyze_text(
    text: str,
    user_input: str = "",
    context: dict[str, Any] | None = None,
    settings: Any | None = None,
) -> dict[str, Any]:
    output = str(text or "")
    low = _norm(output)
    user_low = _norm(user_input)
    paragraphs = _paragraphs(output)
    words = _word_count(output)
    lines = [line.rstrip() for line in output.splitlines()]

    headings = len(re.findall(r"(?m)^\s{0,3}#{1,6}\s+\S", output))
    bullets = len(re.findall(r"(?m)^\s{0,4}(?:[-*+]|\d+\.)\s+\S", output))
    codeblocks = output.count("```") // 2
    avg_para_words = words / max(len(paragraphs), 1)
    long_paras = [i for i, p in enumerate(paragraphs, start=1) if _word_count(p) > 120]
    very_long_lines = [i for i, line in enumerate(lines, start=1) if len(line) > 220]
    collapsed = [pattern.pattern for pattern in FORMAT_COLLAPSE_PATTERNS if pattern.search(output)]

    contrast_count = _count_any(low, CONTRAST_MARKERS)
    uncertainty_count = _count_any(low, UNCERTAINTY_MARKERS)
    absolute_count = _count_any(low, ABSOLUTE_MARKERS)
    evidence_count = _count_any(low, EVIDENCE_MARKERS)
    creative_count = _count_any(low, CREATIVE_MARKERS)
    connection_count = _count_any(low, CONNECTION_MARKERS)

    intent = _context_intent(context)
    claim = _claim_info(context)
    claim_needs_challenge = bool(claim.get("needs_challenge"))
    analytical_context = intent in {"analysis", "philosophical", "technical"} or claim_needs_challenge
    emotional_context = intent == "emotional"

    H = 0.52
    if 2 <= len(paragraphs) <= 14:
        H += 0.16
    if headings or bullets:
        H += 0.10
    if codeblocks:
        H += 0.04
    if avg_para_words <= 90:
        H += 0.10
    if collapsed:
        H -= 0.24
    if long_paras:
        H -= min(0.20, 0.06 * len(long_paras))
    if very_long_lines:
        H -= min(0.15, 0.04 * len(very_long_lines))

    B = 0.48
    if contrast_count:
        B += min(0.20, 0.08 * contrast_count)
    if uncertainty_count:
        B += min(0.12, 0.05 * uncertainty_count)
    if analytical_context and not contrast_count and words > 120:
        B -= 0.18
    if absolute_count:
        B -= min(0.22, 0.06 * absolute_count)
    if words > 550:
        B -= 0.08
    if "ja" in low[:80] and claim_needs_challenge:
        B -= 0.12

    S = 0.46
    if creative_count:
        S += min(0.22, 0.05 * creative_count)
    if bullets:
        S += 0.08
    if "beispiel" in low or "example" in low:
        S += 0.08
    if any(w in user_low for w in ["baue", "idee", "konzept", "architektur", "kreativ", "tool"]):
        S += 0.06
    if words < 45 and intent not in {"greeting", "general"}:
        S -= 0.10
    if words > 750:
        S -= 0.06

    V = 0.50
    if connection_count:
        V += min(0.24, 0.04 * connection_count)
    if _has_any(low, ["user", "nutzer", "person"]):
        V += 0.04
    if "wir" in low or "uns" in low:
        V += 0.06
    if emotional_context and not _has_any(low, ["ich verstehe", "das klingt", "bei dir", "für dich", "fuer dich"]):
        V -= 0.12
    if words > 650 and connection_count <= 1:
        V -= 0.08

    R = 0.78
    if uncertainty_count:
        R += min(0.14, 0.05 * uncertainty_count)
    if evidence_count:
        R += min(0.14, 0.05 * evidence_count)
    if absolute_count:
        R -= min(0.30, 0.08 * absolute_count)
    if claim_needs_challenge and not (contrast_count or uncertainty_count or evidence_count):
        R -= 0.16
    if "ich erfinde" in low or "nicht erfinden" in low:
        R += 0.06

    scores = {"H": _field(H), "B": _field(B), "S": _field(S), "V": _field(V), "R": _field(R)}
    stability = round(min(scores["R"], (scores["H"] * scores["B"] * scores["S"] * scores["V"]) ** 0.25), 3)

    findings: list[dict[str, Any]] = []
    recommendations: list[str] = []

    def add(field: str, severity: str, reason: str, recommendation: str, locations: list[str] | None = None) -> None:
        item = {"field": field, "severity": severity, "reason": reason, "recommendation": recommendation}
        if locations:
            item["locations"] = locations
        findings.append(item)
        recommendations.append(f"{field}: {recommendation}")

    if collapsed:
        add("H", "medium", "Moeglich zusammengeklebte Markdown-Struktur erkannt.", "Absatz-/Markdown-Reparatur pruefen oder kuerzere Abschnitte erzwingen.")
    if long_paras:
        add("H", "medium", "Einzelne Absaetze sind sehr lang.", "Lange Absaetze teilen und je Abschnitt nur eine Kernidee verwenden.", [f"Absatz {i}" for i in long_paras[:4]])
    if analytical_context and not contrast_count and words > 120:
        add("B", "medium", "Analyse-Kontext ohne erkennbare Gegenperspektive.", "Eine kurze Einschraenkung, Gegenposition oder Abwaegung ergaenzen.")
    if absolute_count:
        add("R", "high" if absolute_count >= 3 else "medium", "Absolute oder starke Behauptungen erkannt.", "Staerke der Behauptung an Evidenz koppeln oder vorsichtiger formulieren.", [f"Absatz {i}" for i in _paragraph_indexes(paragraphs, ABSOLUTE_MARKERS)])
    if claim_needs_challenge and not (contrast_count or evidence_count):
        add("R", "high", "Claim Guard sah Pruefbedarf, aber die Antwort zeigt wenig Evidenz-/Gegencheck.", "Bei starken Claims zuerst qualifizieren, dann konstruktiv antworten.")
    if scores["S"] < 0.45 and words > 140:
        add("S", "low", "Antwort ist relativ lang, aber liefert wenig konkrete Ideen oder Beispiele.", "Ein Beispiel, naechsten Schritt oder konkrete Umsetzung ergaenzen.")
    if scores["V"] < 0.45:
        add("V", "low", "Wenig sichtbarer Bezug zu User, Projekt oder Kontext.", "Kurz an Ziel, Projekt oder bisherigen Kontext des Users ankoppeln.")
    if not findings:
        findings.append({"field": "all", "severity": "ok", "reason": "Keine kritischen Muster erkannt.", "recommendation": "Keine Aktion noetig."})

    report = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_input": user_input or "",
        "intent": intent,
        "words": words,
        "paragraphs": len(paragraphs),
        "headings": headings,
        "bullets": bullets,
        "codeblocks": codeblocks,
        "scores": scores,
        "stability": stability,
        "claim_guard": {
            "needs_challenge": claim_needs_challenge,
            "stance": claim.get("stance", "-"),
            "risk_level": claim.get("risk_level", "-"),
        },
        "features": {
            "contrast": bool(contrast_count),
            "uncertainty": bool(uncertainty_count),
            "absolute_claim": bool(absolute_count),
            "evidence_marker": bool(evidence_count),
            "creative_marker": bool(creative_count),
            "connection_marker": bool(connection_count),
            "long_paragraph": bool(long_paras),
            "missing_structure": bool(words > 120 and not (headings or bullets or codeblocks) and len(paragraphs) <= 1),
            "collapsed_markdown": bool(collapsed),
            "very_long_line": bool(very_long_lines),
        },
        "feature_counts": {
            "contrast": contrast_count,
            "uncertainty": uncertainty_count,
            "absolute": absolute_count,
            "evidence": evidence_count,
            "creative": creative_count,
            "connection": connection_count,
        },
        "findings": findings,
        "recommendations": recommendations[:6],
    }
    return _apply_thresholds(report, settings) if settings is not None else report


def score_line(report: dict[str, Any] | None) -> str:
    if not report:
        return "no report yet"
    scores = report.get("scores", {}) or {}
    return (
        f"H={float(scores.get('H', 0)):.2f} | "
        f"B={float(scores.get('B', 0)):.2f} | "
        f"S={float(scores.get('S', 0)):.2f} | "
        f"V={float(scores.get('V', 0)):.2f} | "
        f"R={float(scores.get('R', 0)):.2f} -> "
        f"Stability={float(report.get('stability', 0)):.2f}"
    )


def format_report(report: dict[str, Any] | None = None) -> str:
    report = report or LAST_REPORT
    if not report:
        return "Noch kein MAAT Feedback Report vorhanden."
    lines = [
        "# MAAT Feedback",
        "",
        f"- Zeit: `{report.get('ts', '-')}`",
        f"- Intent: `{report.get('intent', 'general')}`",
        f"- Laenge: {report.get('words', 0)} Woerter, {report.get('paragraphs', 0)} Absaetze",
        f"- Struktur: {report.get('headings', 0)} Headings, {report.get('bullets', 0)} Listenpunkte, {report.get('codeblocks', 0)} Codebloecke",
        f"- Kritisch: {'ja' if report.get('critical') else 'nein'}",
        "",
        "```text",
        score_line(report),
        "```",
        "",
        "## Features",
    ]
    features = report.get("feature_counts", {}) or {}
    lines.extend(
        [
            f"- contrast={features.get('contrast', 0)} uncertainty={features.get('uncertainty', 0)} absolute={features.get('absolute', 0)} evidence={features.get('evidence', 0)}",
            f"- creative={features.get('creative', 0)} connection={features.get('connection', 0)}",
            "",
            "## Findings",
        ]
    )
    for finding in report.get("findings", []) or []:
        loc = ""
        if finding.get("locations"):
            loc = " (" + ", ".join(finding.get("locations")[:4]) + ")"
        lines.append(
            f"- [{finding.get('severity', '-')}] {finding.get('field', '-')}: "
            f"{finding.get('reason', '-')}{loc} -> {finding.get('recommendation', '-')}"
        )
    if report.get("recommendations"):
        lines.extend(["", "## Empfehlungen"])
        for rec in report.get("recommendations", [])[:6]:
            lines.append(f"- {rec}")
    return "\n".join(lines)


def history_text() -> str:
    if not HISTORY:
        return "Noch keine MAAT Feedback History vorhanden."
    lines = ["# MAAT Feedback History", ""]
    for idx, report in enumerate(HISTORY[:20], start=1):
        lines.append(
            f"{idx}. `{report.get('ts', '-')}` intent={report.get('intent', '-')} "
            f"critical={'yes' if report.get('critical') else 'no'} | {score_line(report)}"
        )
    return "\n".join(lines)


def _finding_category(finding: dict[str, Any], intent: str) -> str:
    field = str(finding.get("field") or "").upper()
    reason = _norm(f"{finding.get('reason', '')} {finding.get('recommendation', '')}")
    if field == "H":
        return "style"
    if field == "R":
        return "science" if any(w in reason for w in ["evidenz", "claim", "beweis", "fakt"]) else "wissen"
    if field == "S":
        return "coding" if intent == "technical" else "project"
    if field == "V":
        return "smalltalk"
    if field == "B":
        return "philosophy" if intent in {"analysis", "philosophical"} else "wissen"
    return "wissen"


def _lesson_from_finding(report: dict[str, Any], finding: dict[str, Any]) -> tuple[str, str, str]:
    field = str(finding.get("field") or "-").upper()
    intent = report.get("intent", "general")
    recommendation = str(finding.get("recommendation") or "").strip()
    reason = str(finding.get("reason") or "").strip()
    if field == "H":
        return "style", "style", f"Bei {intent}-Antworten auf saubere Struktur achten: Absaetze, Listen und Markdown pruefen. Ausloeser: {reason}"
    if field == "B":
        return _finding_category(finding, intent), "critical", f"Bei {intent}-Antworten Balance staerken: relevante Gegenperspektive oder Einschraenkung kurz einbauen. Regel: {recommendation}"
    if field == "R":
        return _finding_category(finding, intent), "fact_check", f"Bei {intent}-Antworten Respekt/Wahrheit priorisieren: starke Behauptungen an Evidenz koppeln und Unsicherheit markieren. Regel: {recommendation}"
    if field == "S":
        return _finding_category(finding, intent), "style", f"Bei {intent}-Antworten konkrete Beispiele, naechste Schritte oder Umsetzungsideen ergaenzen. Regel: {recommendation}"
    if field == "V":
        return _finding_category(finding, intent), "style", f"Bei {intent}-Antworten kurz an User-Ziel, Projekt oder bisherigen Kontext ankoppeln. Regel: {recommendation}"
    return "wissen", "critical", f"Bei {intent}-Antworten verbessern: {recommendation or reason}"


def store_self_lessons(database: Database, settings: Any, report: dict[str, Any]) -> list[dict[str, Any]]:
    if not bool(getattr(settings, "feedback_self_learning_enabled", True)):
        return []
    if not report.get("critical"):
        return []
    limit = max(0, min(5, int(getattr(settings, "feedback_self_learning_per_report", 2) or 2)))
    stored: list[dict[str, Any]] = []
    for finding in (report.get("findings") or []):
        if len(stored) >= limit:
            break
        if finding.get("severity") not in {"high", "medium"} or finding.get("field") == "all":
            continue
        category, lesson_type, lesson = _lesson_from_finding(report, finding)
        result = store_lesson(database, lesson, category=category, lesson_type=lesson_type, source="feedback_tool", score=0.95)
        if result.get("stored"):
            stored.append(result)
    return stored


def record_feedback(
    database: Database,
    settings: Any,
    user_input: str,
    output: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    global LAST_REPORT
    if not bool(getattr(settings, "feedback_enabled", True)):
        return {"enabled": False}
    report = analyze_text(output, user_input, context, settings)
    self_lessons = store_self_lessons(database, settings, report)
    report["self_lessons"] = len(self_lessons)
    LAST_REPORT = report
    HISTORY.insert(0, report)
    limit = max(5, min(100, int(getattr(settings, "feedback_history_limit", 25) or 25)))
    del HISTORY[limit:]
    return {"enabled": True, "last": report, "self_lessons": self_lessons}


def status(settings: Any) -> dict[str, Any]:
    return {
        "enabled": bool(getattr(settings, "feedback_enabled", True)),
        "debug": bool(getattr(settings, "feedback_debug", False)),
        "self_learning": bool(getattr(settings, "feedback_self_learning_enabled", True)),
        "history": len(HISTORY),
        "last": LAST_REPORT,
    }


def status_text(settings: Any) -> str:
    return (
        f"MAAT Feedback {'aktiv' if getattr(settings, 'feedback_enabled', True) else 'aus'} "
        f"· Reports {len(HISTORY)} · Self-Learning {'an' if getattr(settings, 'feedback_self_learning_enabled', True) else 'aus'}"
    )


def command_feedback(database: Database, settings: Any, args: list[str]) -> str:
    if not args or args[0].lower() in {"last", "report"}:
        return format_report()
    raw = str(args[0]).lower()
    if raw in {"on", "off"}:
        settings.feedback_enabled = raw == "on"
        return f"MAAT Feedback {'aktiviert' if settings.feedback_enabled else 'deaktiviert'}."
    if raw == "debug":
        settings.feedback_debug = not bool(getattr(settings, "feedback_debug", False))
        return f"MAAT Feedback Debug {'an' if settings.feedback_debug else 'aus'}."
    if raw in {"self", "learning"} and len(args) >= 2:
        settings.feedback_self_learning_enabled = str(args[1]).lower() in {"on", "an", "1", "true", "ja"}
        return f"Feedback Self-Learning {'an' if settings.feedback_self_learning_enabled else 'aus'}."
    if raw == "history":
        return history_text()
    if raw == "test":
        text = " ".join(args[1:]).strip()
        if not text:
            return "Usage: `/maat feedback test <text>`"
        report = analyze_text(text, "", {}, settings)
        return format_report(report)
    if raw == "status":
        return status_text(settings)
    return (
        "MAAT Feedback Befehle: `/maat feedback`, `/maat feedback on|off`, "
        "`/maat feedback debug`, `/maat feedback history`, `/maat feedback self on|off`, "
        "`/maat feedback test <text>`."
    )
