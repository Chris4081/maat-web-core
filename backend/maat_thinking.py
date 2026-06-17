from __future__ import annotations


def normalize_level(value: object) -> int:
    if isinstance(value, str):
        cleaned = value.strip().lower().replace("maat", "").replace("%", "")
        if cleaned in {"off", "aus", "none", "no", "false"}:
            return 0
        value = cleaned
    try:
        level = int(float(value))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, level))


def _target_for_level(level: int) -> float:
    if level <= 0:
        return 0.0
    return round(6.8 + (2.7 * (level / 100.0)), 1)


def _repairs_for_level(level: int) -> int:
    if level <= 0:
        return 0
    if level < 40:
        return 1
    if level < 80:
        return 2
    return 3


def _depth_for_level(level: int) -> str:
    if level <= 0:
        return "off"
    if level < 35:
        return "light"
    if level < 75:
        return "balanced"
    return "deep"


def _hint_for_level(level: int) -> str:
    if level <= 0:
        return "MAAT Thinking ist aus."
    depth = _depth_for_level(level)
    repairs = _repairs_for_level(level)
    target = _target_for_level(level)
    if depth == "light":
        mode = "leichter Schliff für Klarheit, Nähe und Ehrlichkeit"
    elif depth == "balanced":
        mode = "normaler Qualitätscheck nach H/B/S/V/R"
    else:
        mode = "starke Antwortverbesserung mit Fakten-, Balance- und Strukturprüfung"
    return (
        f"MAAT{level}: {mode}. Zielwert intern ca. {target:.1f}/10. "
        f"Maximal {repairs} Repair-Runde{'n' if repairs != 1 else ''}."
    )


def level_status(value: object) -> dict[str, object]:
    level = normalize_level(value)
    return {
        "level": level,
        "label": f"MAAT{level}",
        "target": _target_for_level(level),
        "depth": _depth_for_level(level),
        "enabled": level > 0,
        "hint": _hint_for_level(level),
        "repairs": _repairs_for_level(level),
    }


def _quality_rules(depth: str) -> str:
    common = """Prüfe:
- H = sprachliche und logische Kohärenz
- B = Balance zwischen Tiefe, Nüchternheit und Nähe
- S = Schöpfungskraft als bessere Lösung, nicht als Verzierung
- V = Verbundenheit mit Frage, Nutzer und Kontext
- R = Ehrlichkeit, Würde, Vorsicht, keine Halluzination

Regeln:
- Faktische Fragen konkret und geerdet beantworten.
- Bei fehlendem Wissen ehrlich markieren und trotzdem hilfreich einordnen.
- Bei starken Behauptungen Evidenz, Unsicherheit und Gegenperspektive prüfen.
- Bei einfachen Begrüßungen, Smalltalk und emotionalen Kurzantworten natürlich und kurz bleiben.
- Code, LaTeX, Markdown und Listen nicht kürzen oder beschädigen."""
    if depth == "light":
        return common + "\n- Nur grobe Schwächen reparieren; keine unnötige Länge erzeugen."
    if depth == "balanced":
        return common + "\n- Struktur, Style-Fit und konkrete Nützlichkeit sichtbar verbessern."
    return (
        common
        + "\n- Zusätzlich Quellenlage, Gegenbeispiele, Randfälle, Format und Nutzbarkeit streng prüfen."
    )


def build_prompt_block(value: object, visible_reasoning: bool = False) -> str:
    level = normalize_level(value)
    if level <= 0:
        return ""

    status = level_status(level)
    depth = str(status["depth"])
    target = float(status["target"])
    repairs = int(status["repairs"])
    rules = _quality_rules(depth)

    if visible_reasoning:
        return (
            "\n\n[MAAT_EXTENDED_THINKING]\n"
            f"Antwortverbesserung: MAAT{level} ({level}%).\n"
            f"Zielwert intern: ca. {target:.1f}/10 je Feld.\n"
            f"Maximale Reparaturrunden: {repairs}.\n\n"
            "Wenn das Modell sichtbares Thinking erzeugt, schreibe die Denkphase ausschließlich "
            "in einen <think>...</think>-Block. Darin kurz prüfen: H, B, S, V, R, Schwächen, "
            "Reparaturentscheidung. Nach </think> folgt nur die finale Antwort.\n\n"
            f"{rules}\n"
            "[/MAAT_EXTENDED_THINKING]"
        )

    return (
        "\n\n[MAAT_INTERNAL_QUALITY]\n"
        "Nutze diesen Block nur still zur Qualitätssteuerung. "
        "Niemals zitieren, zusammenfassen oder sichtbar ausgeben.\n\n"
        "[MAAT_QUALITY_CHECK]\n"
        f"Antwortverbesserung: MAAT{level} ({level}%).\n"
        f"Zielwert intern: ca. {target:.1f}/10 je Feld.\n"
        f"Maximale Reparaturrunden: {repairs}.\n\n"
        "Vorgehen:\n"
        "1. Erstelle einen Entwurf.\n"
        "2. Bewerte H, B, S, V, R intern grob von 0 bis 10.\n"
        "3. Wenn ein wichtiges Feld unter dem Zielwert liegt, verbessere den Entwurf still.\n"
        "4. Wiederhole das höchstens bis zur maximalen Reparaturrunde.\n"
        "5. Gib nur die finale Antwort aus.\n\n"
        f"{rules}\n\n"
        "Keine sichtbaren Scores, keine Denkspur, keine Analyseblöcke, keine <think>-Tags.\n"
        "[/MAAT_QUALITY_CHECK]\n"
        "[/MAAT_INTERNAL_QUALITY]"
    )
