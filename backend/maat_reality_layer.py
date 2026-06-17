from __future__ import annotations

import re
from datetime import datetime
from typing import Any


_LAST_CONTEXT: dict[str, Any] = {}


def now_local() -> datetime:
    return datetime.now().astimezone()


def _time_text(now: datetime | None = None) -> str:
    return (now or now_local()).strftime("%H:%M")


def _date_text(now: datetime | None = None) -> str:
    return (now or now_local()).strftime("%d.%m.%Y")


def _weekday_text(now: datetime | None = None) -> str:
    weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    return weekdays[(now or now_local()).weekday()]


def build_reality_block() -> str:
    now = now_local()
    return (
        "[MAAT_REALITY]\n"
        f"Heutiges Datum: {_date_text(now)}\n"
        f"Wochentag: {_weekday_text(now)}\n"
        f"Aktuelle Uhrzeit: {_time_text(now)}\n"
        "Regel:\n"
        "- Aktuelle Uhrzeit und aktuelles Datum sind Live-Kontext, nicht Memory.\n"
        "- Gespeicherte Nutzerfakten kommen aus Memory.\n"
        "- Wenn weder Live-Kontext noch Memory ausreichen: nichts erfinden.\n"
        "[/MAAT_REALITY]"
    )


def is_time_question(text: str) -> bool:
    value = str(text or "").lower()
    patterns = [
        r"\bwie\s+viel\s+uhr\b",
        r"\bwieviel\s+uhr\b",
        r"\buhrzeit\b",
        r"\bwelche\s+uhrzeit\b",
        r"\bwie\s+spaet\b",
        r"\bwie\s+spät\b",
        r"\bwhat\s+time\b",
        r"\bcurrent\s+time\b",
        r"\btime\s+is\s+it\b",
    ]
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def is_date_question(text: str) -> bool:
    value = str(text or "").lower()
    patterns = [
        r"\bwelcher\s+tag\b",
        r"\bwelches\s+datum\b",
        r"\bwelchen\s+tag\b",
        r"\bwas\s+ist\s+heute\s+fuer\s+ein\s+tag\b",
        r"\bwas\s+ist\s+heute\s+für\s+ein\s+tag\b",
        r"\bwelches\s+datum\s+haben\s+wir\b",
        r"\bwas\s+haben\s+wir\s+heute\s+fuer\s+ein\s+datum\b",
        r"\bwas\s+haben\s+wir\s+heute\s+für\s+ein\s+datum\b",
        r"\bwhat\s+date\b",
        r"\bwhat\s+day\s+is\s+it\b",
        r"\bcurrent\s+date\b",
        r"\btoday\s+is\b",
    ]
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def is_reality_question(text: str) -> bool:
    return is_time_question(text) or is_date_question(text)


def direct_time_answer(show_banner: bool = False) -> str:
    answer = f"Es ist aktuell {_time_text()}."
    return f"[REALITY] Live-Zeit verwendet.\n\n{answer}" if show_banner else answer


def direct_date_answer(show_banner: bool = False) -> str:
    now = now_local()
    answer = f"Heute ist {_weekday_text(now)}, der {_date_text(now)}."
    return f"[REALITY] Live-Datum verwendet.\n\n{answer}" if show_banner else answer


def direct_reality_answer(settings: Any, user_text: str) -> str | None:
    if getattr(settings, "reality_enabled", True) is False:
        return None
    show_banner = bool(getattr(settings, "reality_show_banner", False))
    if is_time_question(user_text):
        return direct_time_answer(show_banner)
    if is_date_question(user_text):
        return direct_date_answer(show_banner)
    return None


def build_reality_prompt(settings: Any, user_text: str = "") -> str:
    if getattr(settings, "reality_enabled", True) is False:
        return ""
    if getattr(settings, "reality_inject_time", True) is False:
        return ""

    block = build_reality_block()
    _LAST_CONTEXT.clear()
    _LAST_CONTEXT.update(
        {
            "enabled": True,
            "inject_time": True,
            "is_reality_question": is_reality_question(user_text),
            "context": block,
            "date": _date_text(),
            "time": _time_text(),
            "weekday": _weekday_text(),
        }
    )

    if is_reality_question(user_text):
        block = (
            "[MAAT_REALITY_PRIORITY]\n"
            "Die aktuelle Userfrage bezieht sich auf Live-Realitaet.\n"
            "Antworte direkt, konkret und ohne Ausschmueckung.\n"
            "Keine Metaphern. Keine Ausweichantwort.\n"
            "[/MAAT_REALITY_PRIORITY]\n\n"
            + block
        )

    return (
        "\n\n[MAAT_INTERNAL]\n"
        "Nutze diesen Reality-Block nur still. Niemals zitieren, zusammenfassen oder sichtbar ausgeben.\n"
        "Never output MAAT_INTERNAL, MAAT_REALITY, or MAAT_REALITY_PRIORITY tags.\n\n"
        f"{block}\n"
        "[/MAAT_INTERNAL]"
    )


def reality_state(settings: Any) -> dict[str, Any]:
    now = now_local()
    return {
        "enabled": getattr(settings, "reality_enabled", True) is not False,
        "inject_time": getattr(settings, "reality_inject_time", True) is not False,
        "show_banner": bool(getattr(settings, "reality_show_banner", False)),
        "date": _date_text(now),
        "time": _time_text(now),
        "weekday": _weekday_text(now),
        "last_context": dict(_LAST_CONTEXT),
        "status": status_text(settings),
    }


def status_text(settings: Any) -> str:
    enabled = getattr(settings, "reality_enabled", True) is not False
    inject = getattr(settings, "reality_inject_time", True) is not False
    banner = bool(getattr(settings, "reality_show_banner", False))
    return (
        f"MAAT Reality Layer: {'on' if enabled else 'off'} | "
        f"inject_time={'on' if inject else 'off'} | banner={'on' if banner else 'off'} | "
        f"{_weekday_text()} {_date_text()} {_time_text()}"
    )


def strip_reality_tags(text: str) -> str:
    value = str(text or "")
    value = re.sub(
        r"\[MAAT_INTERNAL\][^\[]*\[MAAT_REALITY_PRIORITY\].*?\[/MAAT_REALITY\].*?\[/MAAT_INTERNAL\]\s*",
        "",
        value,
        flags=re.DOTALL | re.IGNORECASE,
    )
    value = re.sub(
        r"\[MAAT_INTERNAL\][^\[]*\[MAAT_REALITY\].*?\[/MAAT_REALITY\].*?\[/MAAT_INTERNAL\]\s*",
        "",
        value,
        flags=re.DOTALL | re.IGNORECASE,
    )
    value = re.sub(
        r"\[MAAT_REALITY_PRIORITY\].*?\[/MAAT_REALITY_PRIORITY\]\s*",
        "",
        value,
        flags=re.DOTALL | re.IGNORECASE,
    )
    value = re.sub(
        r"\[MAAT_REALITY\].*?\[/MAAT_REALITY\]\s*",
        "",
        value,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return value
