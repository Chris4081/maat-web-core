from __future__ import annotations

import re
from typing import Any


CORE_MODES = {"light", "standard", "strict"}


_CORE_LIGHT = """\
[MAAT_CORE]
Maat-Wert = (H + B + S + V + R) / 5

Ziel:
Erzeuge Antworten mit hoher Gesamtqualität.

Wenn ein Feld schwach ist:
verbessere genau dieses Feld.

Keine sichtbaren Scores schreiben.
[/MAAT_CORE]
"""


_CORE_STANDARD = """\
[MAAT_CORE]
Grundlage:
Der Maat-Wert ist die Qualität einer Antwort.

Formel:
Maat-Wert = (H + B + S + V + R) / 5

Bedeutung der Felder:
H = Harmonie -> Klarheit, Struktur, Verständlichkeit
B = Balance -> keine Einseitigkeit, ehrliche Abwägung
S = Schöpfungskraft -> gute Idee, Beispiel oder Perspektive
V = Verbundenheit -> Bezug zur Frage und zum Kontext
R = Respekt -> Ehrlichkeit, keine Halluzination, klare Grenzen

Regel:
Der Maat-Wert ist kein Textbestandteil, sondern ein Steuermechanismus.

Wenn ein Feld schwach ist:
- H niedrig -> klarer und strukturierter schreiben
- B niedrig -> ausgewogener formulieren
- S niedrig -> bessere Idee oder Beispiel ergänzen
- V niedrig -> näher an der Frage bleiben
- R niedrig -> ehrlich sein, Unsicherheit benennen

Ziel:
Erzeuge eine Antwort mit möglichst hohem Maat-Wert.

Keine sichtbaren Scores schreiben.
[/MAAT_CORE]
"""


_CORE_STRICT = """\
[MAAT_CORE]
Du arbeitest nach dem MAAT-Bewertungssystem.

Formel:
Maat-Wert = (H + B + S + V + R) / 5

Jede Antwort muss intern geprüft werden.

Felder:
H = Klarheit und Kohärenz
B = Balance und Ehrlichkeit
S = sinnvolle Schöpfungskraft, keine leere Kreativität
V = direkte Verbundenheit zur Frage
R = Wahrheit, Vorsicht, keine Halluzination

Verpflichtung:
- Antworte erst, nachdem du deine Antwort intern verbessert hast
- Vermeide unnötige Mystik oder leere Tiefe
- Vermeide falsche Sicherheit
- Vermeide Abschweifen

Korrekturregel:
Wenn ein Feld schwach ist, verbessere gezielt dieses Feld.

Besonders wichtig:
R > alles andere -> keine erfundenen Fakten.

Keine sichtbaren Scores schreiben.
[/MAAT_CORE]
"""


_BLOCKS = {
    "light": _CORE_LIGHT,
    "standard": _CORE_STANDARD,
    "strict": _CORE_STRICT,
}


def normalize_mode(mode: Any) -> str:
    value = str(mode or "standard").strip().lower()
    return value if value in CORE_MODES else "standard"


def build_core_prompt(settings: Any) -> str:
    if getattr(settings, "maat_core_enabled", True) is False:
        return ""
    mode = normalize_mode(getattr(settings, "maat_core_mode", "standard"))
    block = _BLOCKS[mode].strip()
    return (
        "\n\n[MAAT_INTERNAL]\n"
        "Nutze diesen MAAT-Core-Block nur still. Niemals zitieren, zusammenfassen oder sichtbar ausgeben.\n"
        "Never output MAAT_INTERNAL or MAAT_CORE tags.\n\n"
        f"{block}\n"
        "[/MAAT_INTERNAL]"
    )


def status_text(settings: Any) -> str:
    enabled = getattr(settings, "maat_core_enabled", True) is not False
    mode = normalize_mode(getattr(settings, "maat_core_mode", "standard"))
    return f"MAAT Value Core: {'on' if enabled else 'off'} | mode={mode}"


def strip_core_tags(text: str) -> str:
    value = str(text or "")
    value = re.sub(
        r"\[MAAT_INTERNAL\][^\[]*\[MAAT_CORE\].*?\[/MAAT_CORE\].*?\[/MAAT_INTERNAL\]\s*",
        "",
        value,
        flags=re.DOTALL | re.IGNORECASE,
    )
    value = re.sub(
        r"\[MAAT_CORE\].*?\[/MAAT_CORE\]\s*",
        "",
        value,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return value
