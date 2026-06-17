from __future__ import annotations

import re
from typing import Any


MEMORY_ITEM_RE = re.compile(r"^\s*\d+\.\s+\[", re.MULTILINE)


def _settings(settings: Any) -> dict[str, Any]:
    if isinstance(settings, dict):
        return settings
    return getattr(settings, "__dict__", {})


def _setting_bool(settings: Any, key: str, default: bool) -> bool:
    return bool(_settings(settings).get(key, default))


def _setting_int(settings: Any, key: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(_settings(settings).get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _current_user(settings: Any) -> str:
    user = " ".join(str(_settings(settings).get("supermem_current_user") or "User").split())
    return user or "User"


def _approx_tokens(text: str) -> int:
    return max(1, len(str(text or "")) // 4)


def _memory_item_count(memory_prompt: str) -> int:
    return len(MEMORY_ITEM_RE.findall(str(memory_prompt or "")))


def _compact_item_line(line: str, max_chars: int) -> str:
    value = str(line or "").strip()
    if len(value) <= max_chars:
        return value
    return value[: max(20, max_chars - 1)].rstrip() + "…"


def compact_memory_prompt(memory_prompt: str, max_items: int, max_chars: int) -> tuple[str, dict[str, Any]]:
    prompt = str(memory_prompt or "").strip()
    before_chars = len(prompt)
    before_items = _memory_item_count(prompt)
    if not prompt:
        return "", {
            "memory_before_chars": 0,
            "memory_after_chars": 0,
            "memory_before_items": 0,
            "memory_after_items": 0,
            "memory_trimmed": False,
        }

    lines = prompt.splitlines()
    out: list[str] = []
    kept_items = 0
    inside_dropped_item = False
    item_char_budget = max(160, max_chars // max(1, max_items + 2))

    for line in lines:
        stripped = line.strip()
        is_item = bool(re.match(r"^\d+\.\s+\[", stripped))
        if is_item:
            kept_items += 1
            inside_dropped_item = kept_items > max_items
            if inside_dropped_item:
                continue
            out.append(_compact_item_line(line, item_char_budget))
            continue
        if inside_dropped_item:
            if stripped.startswith("[/MAAT_MEMORY]"):
                inside_dropped_item = False
                out.append(line)
            continue
        out.append(line)

    compacted = "\n".join(out).strip()
    if len(compacted) > max_chars:
        closing = "[/MAAT_MEMORY]" if "[/MAAT_MEMORY]" in compacted else ""
        body = compacted.replace("[/MAAT_MEMORY]", "").rstrip()
        compacted = body[: max(80, max_chars - len(closing) - 4)].rstrip() + "\n…"
        if closing:
            compacted = f"{compacted}\n{closing}"

    after_items = _memory_item_count(compacted)
    return compacted, {
        "memory_before_chars": before_chars,
        "memory_after_chars": len(compacted),
        "memory_before_items": before_items,
        "memory_after_items": after_items,
        "memory_trimmed": before_chars != len(compacted) or before_items != after_items,
    }


def build_optimizer_block(settings: Any) -> str:
    if not _setting_bool(settings, "context_optimizer_current_user_block", True):
        return ""
    user = _current_user(settings)
    return (
        "\n\n[MAAT_CONTEXT_OPTIMIZER]\n"
        "Stiller Kontext-Router. Nie zitieren, nie sichtbar ausgeben.\n"
        f"Aktueller menschlicher Schreiber: {user}.\n"
        "Neue User-Aussagen in diesem Turn sind von diesem Schreiber. "
        "Erwähnte Namen im Text sind nur erwähnte Personen, nicht automatisch der Autor.\n"
        "Dieser aktuelle User-Block hat Vorrang vor alten Chat-Titeln, Memory-Zeilen oder älteren User-Hinweisen.\n"
        "Kontextquellen sauber trennen: Super Memory = gespeicherte Erinnerung, Offline Wiki = lokaler ZIM-Kontext, "
        "Project Memory = Projektwissen, Active Lessons = Denkregel.\n"
        "Wenn Quellen fehlen oder widersprechen: Unsicherheit markieren statt raten.\n"
        "[/MAAT_CONTEXT_OPTIMIZER]"
    )


def context_quality(
    *,
    system_text: str,
    memory_prompt: str = "",
    wiki_prompt: str = "",
    project_prompt: str = "",
    lessons_prompt: str = "",
) -> dict[str, Any]:
    text = str(system_text or "")
    tags = re.findall(r"\[MAAT_[A-Z0-9_ -]+", text)
    duplicate_penalty = max(0, len(tags) - len(set(tags))) * 0.25
    memory_chars = len(memory_prompt or "")
    total_chars = max(1, len(text))
    memory_share = memory_chars / total_chars
    sources = sum(1 for block in [memory_prompt, wiki_prompt, project_prompt, lessons_prompt] if str(block or "").strip())
    memory_items = _memory_item_count(memory_prompt)
    current_user_present = "[MAAT_CONTEXT_OPTIMIZER]" in text or "Aktueller menschlicher Schreiber" in text
    source_rules_present = "Kontextquellen sauber trennen" in text or "[MAAT_CONTEXT_SOURCE_STATUS]" in text

    h = max(0.0, min(10.0, 8.4 - duplicate_penalty - max(0.0, memory_share - 0.35) * 4.0))
    b = max(0.0, min(10.0, 8.0 - max(0, memory_items - 6) * 0.35 - max(0.0, memory_share - 0.45) * 5.0))
    s = max(0.0, min(10.0, 6.5 + sources * 0.45 + (0.3 if project_prompt else 0.0)))
    v = max(0.0, min(10.0, 7.0 + (0.8 if current_user_present else 0.0) + min(memory_items, 5) * 0.12))
    r = max(0.0, min(10.0, 7.2 + (0.8 if source_rules_present else 0.0) + (0.4 if current_user_present else 0.0)))
    stability = min(r, (max(h, 0) * max(b, 0) * max(s, 0) * max(v, 0)) ** 0.25)
    return {
        "H": round(h, 2),
        "B": round(b, 2),
        "S": round(s, 2),
        "V": round(v, 2),
        "R": round(r, 2),
        "stability": round(stability, 2),
        "memory_share": round(memory_share, 3),
        "memory_items": memory_items,
        "sources": sources,
        "approx_tokens": _approx_tokens(text),
    }


def optimize_context(
    settings: Any,
    *,
    user_text: str = "",
    memory_prompt: str = "",
    wiki_prompt: str = "",
    project_prompt: str = "",
    lessons_prompt: str = "",
    file_builder_prompt: str = "",
) -> tuple[str, str, dict[str, Any]]:
    enabled = _setting_bool(settings, "context_optimizer_enabled", True)
    info: dict[str, Any] = {
        "enabled": enabled,
        "user": _current_user(settings),
        "query": str(user_text or "")[:160],
    }
    if not enabled:
        info["reason"] = "disabled"
        return "", memory_prompt, info

    max_items = _setting_int(settings, "context_optimizer_max_memory_items", 6, 1, 20)
    max_chars = _setting_int(settings, "context_optimizer_max_memory_chars", 2600, 400, 12000)
    compact_memory, compact_info = compact_memory_prompt(memory_prompt, max_items=max_items, max_chars=max_chars)
    block = build_optimizer_block(settings)
    combined = "".join([block, wiki_prompt or "", lessons_prompt or "", project_prompt or "", file_builder_prompt or "", compact_memory or ""])
    quality = context_quality(
        system_text=combined,
        memory_prompt=compact_memory,
        wiki_prompt=wiki_prompt,
        project_prompt=project_prompt,
        lessons_prompt=lessons_prompt,
    )
    info.update(compact_info)
    info.update(
        {
            "max_memory_items": max_items,
            "max_memory_chars": max_chars,
            "optimizer_block": bool(block),
            "quality": quality,
        }
    )
    return block, compact_memory, info


def report_lines(info: dict[str, Any] | None) -> list[str]:
    data = info or {}
    if not data.get("enabled", True):
        return ["context_optimizer=off"]
    quality = data.get("quality") or {}
    return [
        f"user={data.get('user') or '-'} block={'on' if data.get('optimizer_block') else 'off'}",
        (
            f"memory_items={data.get('memory_after_items', 0)}/{data.get('memory_before_items', 0)} "
            f"memory_chars={data.get('memory_after_chars', 0)}/{data.get('memory_before_chars', 0)} "
            f"trimmed={'yes' if data.get('memory_trimmed') else 'no'}"
        ),
        (
            f"quality H={quality.get('H', 0):.2f} B={quality.get('B', 0):.2f} "
            f"S={quality.get('S', 0):.2f} V={quality.get('V', 0):.2f} R={quality.get('R', 0):.2f} "
            f"stability={quality.get('stability', 0):.2f}"
        ),
        f"sources={quality.get('sources', 0)} approx_tokens={quality.get('approx_tokens', 0)} memory_share={quality.get('memory_share', 0)}",
    ]


def status_text(settings: Any) -> str:
    if not _setting_bool(settings, "context_optimizer_enabled", True):
        return "Context Optimizer aus."
    items = _setting_int(settings, "context_optimizer_max_memory_items", 6, 1, 20)
    chars = _setting_int(settings, "context_optimizer_max_memory_chars", 2600, 400, 12000)
    debug = " · Debug" if _setting_bool(settings, "context_optimizer_debug", False) else ""
    return f"Context Optimizer aktiv · Memory {items} Items/{chars} Zeichen{debug}"
