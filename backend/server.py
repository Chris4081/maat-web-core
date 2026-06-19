from __future__ import annotations

import asyncio
import base64
import hmac
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .chat_loop import ChatLoop
from .commands import CommandRouter
from .config import PLUGIN_DIR, RuntimeSettings, gguf_model_dirs, load_settings, save_settings
from .database import Database, visible_message_text
from .maat_balance import (
    build_balance_prompt,
    normalize_level as normalize_balance_level,
    reset_balance_injection,
    status_text as balance_status_text,
)
from .maat_claim_guard import (
    build_claim_prompt,
    critical_thinking_step,
    get_last_claim,
    normalize_mode as normalize_claim_mode,
    report_lines as claim_report_lines,
    status_text as claim_status_text,
)
from .maat_emotion import (
    build_emotion_prompt,
    evaluate_emotion,
    normalize_language as normalize_emotion_language,
    normalize_mode as normalize_emotion_mode,
    status_text as emotion_status_text,
)
from .maat_engine import evaluate_text, get_last_eval, remember_eval, report_lines
from .maat_cci_engine import (
    compute_advanced_cci,
    get_last_advanced_cci,
    remember_advanced_cci,
    report_lines as advanced_cci_report_lines,
)
from .maat_identity import (
    build_identity_block,
    normalize_mode as normalize_identity_mode,
    normalize_name as normalize_identity_name,
    reset_identity_injection,
    status_text as identity_status_text,
)
from .maat_adaptive_learning import (
    command_lessons,
    initialize_adaptive_learning,
    stats as adaptive_learning_stats,
    why_text as adaptive_learning_why_text,
)
from .maat_feedback_tool import (
    command_feedback,
    format_report as feedback_format_report,
    status as feedback_status,
    status_text as feedback_status_text,
)
from .maat_context_optimizer import status_text as context_optimizer_status_text
from .maat_chat_search import command_chat_search, initialize_chat_search, status_text as chat_search_status_text
from .maat_file_builder import (
    command_docs,
    delete_doc as delete_builder_doc,
    doc_path_by_id,
    file_builder_state,
    open_doc as open_builder_doc,
    run_python_doc,
    save_manual_doc,
)
from .maat_mode_diagnostics import diagnose_mode, report_markdown as mode_report_markdown
from .maat_offline_wiki import command_wiki, status_text as offline_wiki_status_text
from .maat_project_memory import (
    add_entry as project_add_entry,
    add_formula as project_add_formula,
    add_paper as project_add_paper,
    command_project,
    delete_child as project_delete_child,
    format_project_markdown,
    initialize_project_memory,
    project_state,
    search_projects as project_search,
    upsert_project,
)
from .maat_plp_anti_hallu import (
    evaluate_antihallu,
    get_last_antihallu,
    normalize_mode as normalize_antihallu_mode,
    remember_antihallu,
    report_lines as antihallu_report_lines,
    status_text as antihallu_status_text,
)
from .maat_reality_layer import (
    build_reality_prompt,
    direct_date_answer,
    direct_time_answer,
    reality_state,
    status_text as reality_status_text,
)
from .maat_reflection import get_last_reflection, report_lines as reflection_report_lines, status_text as reflection_status_text
from .maat_rewrite_loop import (
    get_last_rewrite,
    normalize_mode as normalize_rewrite_mode,
    report_lines as rewrite_report_lines,
    status_text as rewrite_status_text,
)
from .maat_spirit import SpiritSettings, normalize_mode, spirit_status
from .maat_style import (
    build_style_prompt,
    normalize_density_mode,
    normalize_emoji_mode,
    normalize_heading_mode,
    normalize_list_mode,
    normalize_old_smiley_mode,
    normalize_opening_mode,
    normalize_tone_mode,
    status_text as style_status_text,
)
from .maat_super_memory import (
    command_graph as supermem_command_graph,
    command_memory as supermem_command_memory,
    command_person as supermem_command_person,
    command_timeline as supermem_command_timeline,
    initialize_super_memory,
    person_graph_delete,
    person_graph_state,
    person_graph_upsert,
    stats as supermem_stats,
)
from .maat_memory_dreaming import run_memory_dreaming
from .maat_thinking import level_status, normalize_level
from .maat_value_core import build_core_prompt, normalize_mode as normalize_core_mode, status_text as core_status_text
from .models.llama_cpp_direct import clear_model_cache
from .plugins import PluginManager
from .system_scan import apply_auto_loader_settings, system_scan


STATIC_DIR = Path(__file__).resolve().parent / "static"


ACCESS_DENIED_HTML = """\
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zugriff verweigert · MAAT Web Core</title>
  <style>
    :root { color-scheme: light dark; }
    body {
      min-height: 100vh;
      margin: 0;
      display: grid;
      place-items: center;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0b1110;
      color: #eef8f4;
    }
    main {
      width: min(520px, calc(100vw - 32px));
      border: 1px solid rgba(121, 207, 181, 0.35);
      border-radius: 14px;
      padding: 28px;
      background: rgba(255, 255, 255, 0.055);
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
    }
    h1 { margin: 0 0 10px; font-size: 1.35rem; }
    p { margin: 0; line-height: 1.55; color: #c9d9d4; }
    .hint { margin-top: 14px; font-size: 0.92rem; color: #9fb6af; }
  </style>
</head>
<body>
  <main>
    <h1>Zugriff verweigert</h1>
    <p>Das Passwort wurde falsch eingegeben oder die Anmeldung wurde abgebrochen.</p>
    <p class="hint">Schließe diesen Tab oder lade die Seite neu, um dich erneut anzumelden.</p>
  </main>
</body>
</html>
"""


def auth_credentials() -> tuple[str, str] | None:
    enabled = str(os.environ.get("MAAT_WEB_AUTH_ENABLED", "1")).strip().lower()
    if enabled in {"0", "false", "off", "no", "nein"}:
        return None
    user = str(os.environ.get("MAAT_WEB_AUTH_USER", "")).strip()
    password = str(os.environ.get("MAAT_WEB_AUTH_PASSWORD", ""))
    if not user and not password:
        return None
    if not user or not password:
        print(
            "[MAAT Web Core] Basic Auth unvollständig: MAAT_WEB_AUTH_USER und MAAT_WEB_AUTH_PASSWORD setzen.",
            flush=True,
        )
        return None
    return user, password


class WebCoreRuntime:
    def __init__(self):
        self.settings = load_settings()
        self.database = Database()
        self.database.initialize()
        initialize_super_memory(self.database)
        initialize_adaptive_learning(self.database)
        initialize_project_memory(self.database)
        initialize_chat_search(self.database, self.settings)
        if getattr(self.settings, "supermem_dream_on_load", False):
            try:
                run_memory_dreaming(self.database, self.settings)
            except Exception as exc:
                print(f"[MAAT Web Core][memory_dreaming] startup failed: {exc}")
        self.plugins = PluginManager([PLUGIN_DIR])
        self.plugins.load_all()
        self.commands = CommandRouter()
        self.speech_process: subprocess.Popen[str] | None = None
        self._register_commands()
        self.plugins.register_commands(self.commands)
        self.plugins.call_startup({"database": self.database})

    def _register_commands(self) -> None:
        self.commands.register("/help", lambda args, ctx: self.commands.help_text(), "Zeigt alle Befehle.", aliases=["/h"])
        self.commands.register("/plugins", lambda args, ctx: self.plugins.info_json(), "Zeigt geladene Plugins.")
        self.commands.register(
            "/status",
            lambda args, ctx: (
                f"Adapter: `{self.settings.model_adapter}`\n"
                f"API: `{self.settings.api_base}`\n"
                f"Modell: `{self.settings.model_name}`\n"
                f"DB: `{self.database.path}`"
            ),
            "Zeigt Runtime-Status.",
        )
        self.commands.register(
            "/maat",
            self._maat_command,
            "MAAT-Befehle, z.B. `/maat thinking`, `/maat mode`, `/maat lessons`, `/maat feedback`, `/maat search`, `/maat project`, `/maat docs`, `/maat why`, `/maat core`, `/maat reality`, `/maat memory`, `/maat style`, `/maat claim`, `/maat rewrite`, `/maat balance`, `/maat emotion`, `/maat spirit`, `/maat engine`, `/maat cci`, `/maat reflection`, `/maat antihallu`, `/maat identity`, `/maat wiki`.",
        )

    def _maat_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return "MAAT Befehle: `/maat thinking`, `/maat mode`, `/maat lessons`, `/maat feedback`, `/maat search`, `/maat project`, `/maat docs`, `/maat why`, `/maat core`, `/maat reality`, `/maat time`, `/maat date`, `/maat memory`, `/maat graph`, `/maat person`, `/maat timeline`, `/maat milestones`, `/maat style`, `/maat claim`, `/maat rewrite`, `/maat balance`, `/maat emotion`, `/maat spirit`, `/maat engine`, `/maat cci`, `/maat reflection`, `/maat antihallu`, `/maat identity`, `/maat wiki`."
        if args[0] != "thinking":
            if args[0] in {"help", "commands", "hilfe"}:
                return self.help_markdown()
            if args[0] == "status":
                return self.system_status_markdown()
            if args[0] == "mode":
                return self._maat_mode_command(args[1:], ctx)
            if args[0] == "lessons":
                result = command_lessons(self.database, self.settings, args[1:])
                save_settings(self.settings)
                return result
            if args[0] == "feedback":
                result = command_feedback(self.database, self.settings, args[1:])
                save_settings(self.settings)
                return result
            if args[0] == "search" or (args[0] in {"chat", "archive", "archiv"} and len(args) >= 2 and args[1] == "search"):
                search_args = args[1:] if args[0] == "search" else args[2:]
                result = command_chat_search(self.database, self.settings, search_args)
                save_settings(self.settings)
                return result
            if args[0] in {"project", "projects"}:
                result = command_project(self.database, self.settings, args[1:])
                save_settings(self.settings)
                return result
            if args[0] in {"docs", "doc", "files", "file"}:
                return command_docs(self.settings, args[1:])
            if args[0] == "why":
                learning = adaptive_learning_why_text()
                feedback = feedback_format_report()
                if feedback.startswith("Noch kein"):
                    return learning
                return f"{learning}\n\n---\n\n{feedback}"
            if args[0] == "time":
                return direct_time_answer(bool(self.settings.reality_show_banner))
            if args[0] == "date":
                return direct_date_answer(bool(self.settings.reality_show_banner))
            if args[0] == "memory":
                result = supermem_command_memory(self.database, self.settings, args[1:])
                save_settings(self.settings)
                return result
            if args[0] == "graph":
                return supermem_command_graph(self.database, self.settings, args[1:])
            if args[0] == "person":
                return supermem_command_person(self.database, self.settings, args[1:])
            if args[0] == "timeline":
                return supermem_command_timeline(self.database, self.settings, args[1:], milestones=False)
            if args[0] == "milestones":
                return supermem_command_timeline(self.database, self.settings, args[1:], milestones=True)
            if args[0] == "spirit":
                return self._maat_spirit_command(args[1:], ctx)
            if args[0] == "style":
                return self._maat_style_command(args[1:], ctx)
            if args[0] == "claim":
                return self._maat_claim_command(args[1:], ctx)
            if args[0] == "rewrite":
                return self._maat_rewrite_command(args[1:], ctx)
            if args[0] == "core":
                return self._maat_core_command(args[1:], ctx)
            if args[0] == "reality":
                return self._maat_reality_command(args[1:], ctx)
            if args[0] == "balance":
                return self._maat_balance_command(args[1:], ctx)
            if args[0] == "emotion":
                return self._maat_emotion_command(args[1:], ctx)
            if args[0] == "engine":
                return self._maat_engine_command(args[1:], ctx)
            if args[0] == "cci":
                return self._maat_cci_command(args[1:], ctx)
            if args[0] == "reflection":
                return self._maat_reflection_command(args[1:], ctx)
            if args[0] in {"antihallu", "anti-hallu", "hallu"}:
                return self._maat_antihallu_command(args[1:], ctx)
            if args[0] == "identity":
                return self._maat_identity_command(args[1:], ctx)
            if args[0] == "wiki":
                result = command_wiki(self.settings, args[1:])
                save_settings(self.settings)
                return result
            return f"Unbekannter MAAT-Befehl `{' '.join(args)}`."

        if len(args) == 1:
            info = level_status(self.settings.maat_thinking_level)
            return (
                f"MAAT Thinking: {info['label']} | "
                f"enabled={info['enabled']} | depth={info['depth']} | "
                f"target={info['target']} | repairs={info['repairs']}"
            )

        raw = str(args[1]).lower()
        if raw in {"off", "aus", "0"}:
            level = 0
        elif raw in {"on", "an"}:
            level = 50
        else:
            level = normalize_level(raw)

        self.settings.maat_thinking_level = level
        save_settings(self.settings)
        info = level_status(level)
        return (
            f"MAAT Thinking gespeichert: {info['label']} | depth={info['depth']} | "
            f"target={info['target']} | repairs={info['repairs']}"
        )

    def _last_user_text_for_mode(self, chat_id: int | None) -> str:
        if not chat_id:
            return ""
        for message in reversed(self.database.recent_messages(chat_id, limit=30)):
            if message.get("role") != "user":
                continue
            content = visible_message_text(str(message.get("content") or "")).strip()
            if not content:
                continue
            if content.lower().startswith("/maat"):
                continue
            return content
        return ""

    def _maat_mode_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        raw = " ".join(args).strip()
        if raw.lower() in {"help", "hilfe", "commands"}:
            return (
                "MAAT Mode Diagnose: `/maat mode` nutzt den letzten User-Satz. "
                "`/maat mode test <text>` prüft einen konkreten Text. "
                "Nur Anzeige, keine zusätzliche Prompt-Injection."
            )
        if args and args[0].lower() in {"test", "show", "check", "preview"}:
            text = " ".join(args[1:]).strip()
        elif raw:
            text = raw
        else:
            text = self._last_user_text_for_mode(ctx.get("chat_id"))

        if not text:
            return (
                "MAAT Mode Diagnose: Noch kein letzter User-Satz gefunden.\n\n"
                "Nutze z.B. `/maat mode test hallo maat ki` oder `/maat mode test schreibe python code`."
            )

        return mode_report_markdown(diagnose_mode(self.settings, text))

    def _maat_reality_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return reality_status_text(self.settings)

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.reality_enabled = raw == "on"
            save_settings(self.settings)
            return f"MAAT Reality Layer {'aktiviert' if self.settings.reality_enabled else 'deaktiviert'}."
        if raw in {"inject", "time", "zeit"} and len(args) >= 2:
            self.settings.reality_inject_time = str(args[1]).lower() in {"on", "true", "1", "ja", "an"}
            save_settings(self.settings)
            return f"Reality Live-Kontext {'an' if self.settings.reality_inject_time else 'aus'}."
        if raw == "banner" and len(args) >= 2:
            self.settings.reality_show_banner = str(args[1]).lower() in {"on", "true", "1", "ja", "an"}
            save_settings(self.settings)
            return f"Reality Banner {'an' if self.settings.reality_show_banner else 'aus'}."
        if raw == "preview":
            text = " ".join(args[1:]).strip()
            return "```text\n" + build_reality_prompt(self.settings, text).strip() + "\n```"

        return (
            "MAAT Reality Befehle: `/maat reality`, `/maat reality on|off`, "
            "`/maat reality inject on|off`, `/maat reality banner on|off`, "
            "`/maat reality preview [frage]`, `/maat time`, `/maat date`."
        )

    def _maat_core_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return core_status_text(self.settings)

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.maat_core_enabled = raw == "on"
            save_settings(self.settings)
            return f"MAAT Value Core {'aktiviert' if self.settings.maat_core_enabled else 'deaktiviert'}."
        if raw == "mode" and len(args) >= 2:
            self.settings.maat_core_mode = normalize_core_mode(args[1])
            save_settings(self.settings)
            return f"MAAT Value Core mode={self.settings.maat_core_mode} gespeichert."
        if raw in {"light", "standard", "strict"}:
            self.settings.maat_core_mode = normalize_core_mode(raw)
            self.settings.maat_core_enabled = True
            save_settings(self.settings)
            return f"MAAT Value Core mode={self.settings.maat_core_mode} gespeichert."
        if raw == "preview":
            return "```text\n" + build_core_prompt(self.settings).strip() + "\n```"

        return (
            "MAAT Core Befehle: `/maat core`, `/maat core on|off`, "
            "`/maat core mode light|standard|strict`, `/maat core preview`."
        )

    def _spirit_settings(self) -> SpiritSettings:
        return SpiritSettings(
            enabled=bool(self.settings.spirit_enabled),
            mode=self.settings.spirit_mode,
            language=self.settings.spirit_language,
            once=bool(self.settings.spirit_once),
            use_emojis=bool(self.settings.spirit_use_emojis),
        )

    def _maat_spirit_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            info = spirit_status(self._spirit_settings())
            return (
                f"MAAT Spirit: {'on' if info['enabled'] else 'off'} | "
                f"mode={info['mode']} | lang={info['language']} | once={info['once']} | emojis={info['use_emojis']}"
            )

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.spirit_enabled = raw == "on"
        elif raw == "mode" and len(args) >= 2:
            self.settings.spirit_mode = normalize_mode(args[1])
            self.settings.spirit_enabled = True
        elif raw in {"compact", "standard", "full"}:
            self.settings.spirit_mode = normalize_mode(raw)
            self.settings.spirit_enabled = True
        elif raw == "lang" and len(args) >= 2:
            lang = str(args[1]).lower()
            self.settings.spirit_language = lang if lang in {"auto", "de", "en"} else "auto"
        elif raw == "once" and len(args) >= 2:
            self.settings.spirit_once = str(args[1]).lower() in {"on", "true", "1", "ja"}
        elif raw == "emojis" and len(args) >= 2:
            self.settings.spirit_use_emojis = str(args[1]).lower() in {"on", "true", "1", "ja"}
        else:
            return (
                "MAAT Spirit Befehle: `/maat spirit`, `/maat spirit on|off`, "
                "`/maat spirit mode compact|standard|full`, `/maat spirit lang auto|de|en`, "
                "`/maat spirit once on|off`, `/maat spirit emojis on|off`."
            )

        save_settings(self.settings)
        info = spirit_status(self._spirit_settings())
        return (
            f"MAAT Spirit gespeichert: {'on' if info['enabled'] else 'off'} | "
            f"mode={info['mode']} | lang={info['language']} | once={info['once']} | emojis={info['use_emojis']}"
        )

    def _maat_style_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return style_status_text(self.settings)

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.style_enabled = raw == "on"
        elif raw == "debug":
            self.settings.style_debug = not bool(self.settings.style_debug)
        elif raw == "emoji" and len(args) >= 2:
            self.settings.style_emoji_mode = normalize_emoji_mode(" ".join(args[1:]))
        elif raw in {"smiley", "smilies", "oldsmiley", "old-smiley"} and len(args) >= 2:
            self.settings.style_old_smiley_mode = normalize_old_smiley_mode(" ".join(args[1:]))
        elif raw == "tone" and len(args) >= 2:
            if args[1].lower() == "auto" and len(args) >= 3:
                self.settings.style_tone_auto = args[2].lower() in {"on", "true", "1", "ja"}
            else:
                self.settings.style_tone_mode = normalize_tone_mode(" ".join(args[1:]))
        elif raw in {"opening", "opener", "start", "anrede", "anfang"} and len(args) >= 2:
            self.settings.style_opening_mode = normalize_opening_mode(" ".join(args[1:]))
        elif raw in {"density", "dichte", "absatz", "absätze", "absaetze"} and len(args) >= 2:
            self.settings.style_density_mode = normalize_density_mode(" ".join(args[1:]))
        elif raw in {"headings", "heading", "überschriften", "ueberschriften"} and len(args) >= 2:
            self.settings.style_heading_mode = normalize_heading_mode(" ".join(args[1:]))
        elif raw in {"lists", "list", "listen", "liste"} and len(args) >= 2:
            self.settings.style_list_mode = normalize_list_mode(" ".join(args[1:]))
        elif raw == "greeting" and len(args) >= 2:
            self.settings.style_greeting_override = args[1].lower() in {"on", "true", "1", "ja"}
        elif raw == "test" and len(args) >= 2:
            text = " ".join(args[1:])
            _, info = build_style_prompt(self.settings, text)
            return (
                f"Intent: {info['intent']}\n"
                f"Rules: max_words={info['rules'].get('max_words')} structure={info['rules'].get('structure')}\n"
                f"Tone: {info['tone_mode']} vector={info['tone_vector']}\n"
                f"Opening={info['opening_mode']} density={info['density_mode']} headings={info['heading_mode']} "
                f"lists={info['list_mode']} emojis={info['emoji_mode']} smileys={info['old_smiley_mode']}"
            )
        else:
            return (
                "MAAT Style Befehle: `/maat style`, `/maat style on|off`, "
                "`/maat style emoji none|few|many`, `/maat style smiley none|few|many`, "
                "`/maat style tone neutral|friendly|enthusiastic|scientific|mentor|philosophical`, "
                "`/maat style tone auto on|off`, `/maat style opening direct|varied|warm|personal`, "
                "`/maat style density compact|normal|airy`, `/maat style headings none|simple|rich`, "
                "`/maat style lists none|bullets|numbers|auto`, `/maat style test <text>`."
            )

        save_settings(self.settings)
        return style_status_text(self.settings)

    def _maat_claim_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return claim_status_text(self.settings)

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.claim_guard_enabled = raw == "on"
            save_settings(self.settings)
            return f"MAAT Claim Guard {'aktiviert' if self.settings.claim_guard_enabled else 'deaktiviert'}."
        if raw == "mode" and len(args) >= 2:
            self.settings.claim_guard_mode = normalize_claim_mode(args[1])
            self.settings.claim_guard_enabled = True
            save_settings(self.settings)
            return f"Claim Guard mode={self.settings.claim_guard_mode} gespeichert."
        if raw in {"light", "balanced", "firm"}:
            self.settings.claim_guard_mode = normalize_claim_mode(raw)
            self.settings.claim_guard_enabled = True
            save_settings(self.settings)
            return f"Claim Guard mode={self.settings.claim_guard_mode} gespeichert."
        if raw in {"output", "after", "after_output"} and len(args) >= 2:
            self.settings.claim_guard_after_output = str(args[1]).lower() in {"on", "true", "1", "ja", "an"}
            save_settings(self.settings)
            return f"Claim Guard Output-Repair {'an' if self.settings.claim_guard_after_output else 'aus'}."
        if raw == "banner" and len(args) >= 2:
            self.settings.claim_guard_show_banner = str(args[1]).lower() in {"on", "true", "1", "ja", "an"}
            save_settings(self.settings)
            return f"Claim Guard Banner {'an' if self.settings.claim_guard_show_banner else 'aus'}."
        if raw == "test" and len(args) >= 2:
            text = " ".join(args[1:]).strip()
            result = critical_thinking_step(text)
            return "\n".join(claim_report_lines(result))
        if raw == "preview":
            text = " ".join(args[1:]).strip() or "MAAT ist wissenschaftlich bewiesen."
            block, info = build_claim_prompt(self.settings, text)
            return (
                "\n".join(claim_report_lines(info))
                + "\n\n```text\n"
                + (block.strip() or "[kein Claim-Guard-Block nötig]")
                + "\n```"
            )
        if raw == "last":
            return "\n".join(claim_report_lines(get_last_claim()))

        return (
            "MAAT Claim Guard Befehle: `/maat claim`, `/maat claim on|off`, "
            "`/maat claim mode light|balanced|firm`, `/maat claim output on|off`, "
            "`/maat claim banner on|off`, `/maat claim test <text>`, "
            "`/maat claim preview <text>`, `/maat claim last`."
        )

    def _maat_rewrite_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return rewrite_status_text(self.settings)

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.rewrite_enabled = raw == "on"
            save_settings(self.settings)
            return f"MAAT Rewrite {'aktiviert' if self.settings.rewrite_enabled else 'deaktiviert'}."
        if raw == "mode" and len(args) >= 2:
            self.settings.rewrite_mode = normalize_rewrite_mode(args[1])
            save_settings(self.settings)
            return f"Rewrite mode={self.settings.rewrite_mode} gespeichert."
        if raw in {"light", "balanced", "strict"}:
            self.settings.rewrite_mode = normalize_rewrite_mode(raw)
            self.settings.rewrite_enabled = True
            save_settings(self.settings)
            return f"Rewrite mode={self.settings.rewrite_mode} gespeichert."
        if raw in {"trim", "shorten", "kuerzen", "kürzen"} and len(args) >= 2:
            self.settings.rewrite_trim_outputs = str(args[1]).lower() in {"on", "true", "1", "ja", "an"}
            save_settings(self.settings)
            return f"Rewrite Kürzen {'an' if self.settings.rewrite_trim_outputs else 'aus'}."
        if raw == "banner" and len(args) >= 2:
            self.settings.rewrite_show_banner = str(args[1]).lower() in {"on", "true", "1", "ja", "an"}
            save_settings(self.settings)
            return f"Rewrite Banner {'an' if self.settings.rewrite_show_banner else 'aus'}."
        if raw == "threshold" and len(args) >= 3:
            target = str(args[1]).lower()
            try:
                value = float(args[2])
            except (TypeError, ValueError):
                return "Usage: /maat rewrite threshold weak|strong|rmin <zahl>"
            if target == "weak":
                self.settings.rewrite_field_weak = max(0.0, min(value, 10.0))
            elif target == "strong":
                self.settings.rewrite_field_strong = max(0.0, min(value, 10.0))
            elif target in {"rmin", "r"}:
                self.settings.rewrite_r_min = max(0.0, min(value, 10.0))
            else:
                return "Usage: /maat rewrite threshold weak|strong|rmin <zahl>"
            save_settings(self.settings)
            return rewrite_status_text(self.settings)
        if raw == "last":
            return "\n".join(rewrite_report_lines(get_last_rewrite()))

        return (
            "MAAT Rewrite Befehle: `/maat rewrite`, `/maat rewrite on|off`, "
            "`/maat rewrite mode light|balanced|strict`, `/maat rewrite trim on|off`, "
            "`/maat rewrite banner on|off`, `/maat rewrite threshold weak|strong|rmin <zahl>`, "
            "`/maat rewrite last`."
        )

    def _maat_balance_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return balance_status_text(self.settings)

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.balance_enabled = raw == "on"
            reset_balance_injection()
            save_settings(self.settings)
            return f"MAAT Balance {'aktiviert' if self.settings.balance_enabled else 'deaktiviert'}."
        if raw == "level" and len(args) >= 2:
            self.settings.balance_level = normalize_balance_level(args[1])
            reset_balance_injection()
            save_settings(self.settings)
            return f"Balance Level={self.settings.balance_level} gespeichert."
        if raw in {"soft", "standard", "firm"}:
            self.settings.balance_level = normalize_balance_level(raw)
            reset_balance_injection()
            save_settings(self.settings)
            return f"Balance Level={self.settings.balance_level} gespeichert."
        if raw == "debug":
            self.settings.balance_debug = not bool(self.settings.balance_debug)
            save_settings(self.settings)
            return f"Balance Debug {'an' if self.settings.balance_debug else 'aus'}."
        if raw == "once" and len(args) >= 2:
            self.settings.balance_once = str(args[1]).lower() in {"on", "true", "1", "ja"}
            reset_balance_injection()
            save_settings(self.settings)
            return f"Balance once {'an' if self.settings.balance_once else 'aus'}."
        if raw in {"self", "selfreflect", "self-reflect", "reflexion"} and len(args) >= 2:
            self.settings.balance_self_reflect = str(args[1]).lower() in {"on", "true", "1", "ja"}
            reset_balance_injection()
            save_settings(self.settings)
            return f"Balance Selbstreflexion {'an' if self.settings.balance_self_reflect else 'aus'}."
        if raw == "dynamic":
            self.settings.balance_dynamic = not bool(self.settings.balance_dynamic)
            reset_balance_injection()
            save_settings(self.settings)
            return f"B_dynamic Regler {'an' if self.settings.balance_dynamic else 'aus'}."
        if raw in {"context", "weights", "gewichtung"}:
            self.settings.balance_context_weights = not bool(self.settings.balance_context_weights)
            reset_balance_injection()
            save_settings(self.settings)
            return f"Balance Kontext-Gewichtung {'an' if self.settings.balance_context_weights else 'aus'}."
        if raw in {"counterpart", "gegenueber", "gegenüber"}:
            self.settings.balance_counterpart_mode = not bool(self.settings.balance_counterpart_mode)
            reset_balance_injection()
            save_settings(self.settings)
            return f"Gegenüber-Modus {'an' if self.settings.balance_counterpart_mode else 'aus'}."
        if raw == "reset":
            reset_balance_injection()
            return "Balance Session zurückgesetzt."
        if raw == "preview":
            text = " ".join(args[1:]).strip() or "MAAT ist wissenschaftlich bewiesen, oder?"
            block, info = build_balance_prompt(self.settings, text, chat_id=None)
            return (
                f"Balance preview: level={info.get('level')} context={info.get('context_type')} "
                f"pressure={info.get('agreement_pressure')} skip={info.get('skip')}\n\n"
                "```text\n"
                f"{block or '[kein Block injiziert]'}\n"
                "```"
            )

        return (
            "MAAT Balance Befehle: `/maat balance`, `/maat balance on|off`, "
            "`/maat balance level soft|standard|firm`, `/maat balance dynamic`, "
            "`/maat balance context`, `/maat balance counterpart`, `/maat balance debug`, "
            "`/maat balance once on|off`, `/maat balance self on|off`, `/maat balance reset`, "
            "`/maat balance preview <text>`."
        )

    def _maat_emotion_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return emotion_status_text(self.settings)

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.emotion_enabled = raw == "on"
        elif raw == "debug":
            self.settings.emotion_debug = not bool(self.settings.emotion_debug)
        elif raw == "mode" and len(args) >= 2:
            self.settings.emotion_mode = normalize_emotion_mode(args[1])
            self.settings.emotion_enabled = True
        elif raw in {"detect", "simulate", "full"}:
            self.settings.emotion_mode = normalize_emotion_mode(raw)
            self.settings.emotion_enabled = True
        elif raw in {"lang", "language", "sprache"} and len(args) >= 2:
            self.settings.emotion_language = normalize_emotion_language(args[1])
        elif raw == "eval" and len(args) >= 2:
            text = " ".join(args[1:]).strip()
            prompt, state = build_emotion_prompt(self.settings, text, last_eval=get_last_eval())
            result = state.get("result")
            if not result:
                return "Keine Emotion erkannt."
            return (
                f"{result['text']}\n"
                f"Effekte: {result['maat_adjusts']}\n"
                f"Simulation: {result['simulation']}\n"
                f"Prompt aktiv: {'ja' if prompt else 'nein'}"
            )
        elif raw == "raw" and len(args) >= 2:
            text = " ".join(args[1:]).strip()
            lang = normalize_emotion_language(self.settings.emotion_language)
            if lang == "auto":
                lang = "de"
            result = evaluate_emotion(text, lang=lang)
            if not result:
                return "Keine Emotion erkannt."
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            return (
                "MAAT Emotion Befehle: `/maat emotion`, `/maat emotion on|off`, "
                "`/maat emotion mode detect|simulate|full`, `/maat emotion lang auto|de|en`, "
                "`/maat emotion debug`, `/maat emotion eval <text>`."
            )

        save_settings(self.settings)
        return emotion_status_text(self.settings)

    def _maat_engine_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            last = get_last_eval()
            last_text = last["text"] if last else "None"
            return f"MAAT Engine: {'on' if self.settings.engine_enabled else 'off'} | last={last_text}"

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.engine_enabled = raw == "on"
            save_settings(self.settings)
            return f"MAAT Engine {'aktiviert' if self.settings.engine_enabled else 'deaktiviert'}."
        if raw == "show" and len(args) >= 2:
            self.settings.engine_show_in_chat = str(args[1]).lower() in {"on", "true", "1", "ja"}
            save_settings(self.settings)
            return f"MAAT Engine Chat-Anzeige {'an' if self.settings.engine_show_in_chat else 'aus'}."
        if raw == "cci" and len(args) >= 2:
            self.settings.engine_show_cci_debug = str(args[1]).lower() in {"on", "true", "1", "ja"}
            save_settings(self.settings)
            return f"MAAT Engine CCI-Debug {'an' if self.settings.engine_show_cci_debug else 'aus'}."
        if raw == "eval":
            text = " ".join(args[1:]).strip()
            if not text:
                return "Usage: /maat engine eval <text>"
            result = evaluate_text(text)
            remember_eval(result)
            return "\n".join(report_lines(result))

        return "MAAT Engine Befehle: `/maat engine`, `/maat engine on|off`, `/maat engine show on|off`, `/maat engine cci on|off`, `/maat engine eval <text>`."

    def _maat_cci_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            last = get_last_advanced_cci()
            last_text = last["text"] if last else "None"
            return (
                f"Advanced CCI: {'on' if self.settings.advanced_cci_enabled else 'off'} | "
                f"debug={'on' if self.settings.advanced_cci_show_debug else 'off'} | "
                f"kappa={self.settings.advanced_cci_kappa} | last={last_text}"
            )

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.advanced_cci_enabled = raw == "on"
            save_settings(self.settings)
            return f"Advanced CCI {'aktiviert' if self.settings.advanced_cci_enabled else 'deaktiviert'}."
        if raw == "debug" and len(args) >= 2:
            self.settings.advanced_cci_show_debug = str(args[1]).lower() in {"on", "true", "1", "ja"}
            save_settings(self.settings)
            return f"Advanced CCI Debug {'an' if self.settings.advanced_cci_show_debug else 'aus'}."
        if raw == "kappa" and len(args) >= 2:
            try:
                self.settings.advanced_cci_kappa = max(0.0, min(float(args[1]), 5.0))
            except (TypeError, ValueError):
                return "Usage: /maat cci kappa <0.0-5.0>"
            save_settings(self.settings)
            return f"Advanced CCI kappa={self.settings.advanced_cci_kappa:.3f} gespeichert."
        if raw == "eval":
            text = " ".join(args[1:]).strip()
            if not text:
                return "Usage: /maat cci eval <text>"
            maat_eval = evaluate_text(text)
            result = compute_advanced_cci(text, text, maat_eval, kappa=self.settings.advanced_cci_kappa)
            remember_advanced_cci(result)
            return "\n".join(advanced_cci_report_lines(result))

        return "MAAT CCI Befehle: `/maat cci`, `/maat cci on|off`, `/maat cci debug on|off`, `/maat cci kappa <zahl>`, `/maat cci eval <text>`."

    def _maat_reflection_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return reflection_status_text(self.settings)

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.reflection_enabled = raw == "on"
            save_settings(self.settings)
            return f"MAAT Reflection {'aktiviert' if self.settings.reflection_enabled else 'deaktiviert'}."
        if raw == "banner" and len(args) >= 2:
            self.settings.reflection_banner = str(args[1]).lower() in {"on", "true", "1", "ja"}
            save_settings(self.settings)
            return f"Reflection Banner {'an' if self.settings.reflection_banner else 'aus'}."
        if raw == "mode" and len(args) >= 2:
            mode = str(args[1]).lower()
            if mode not in {"auto", "manual"}:
                return "Usage: /maat reflection mode auto|manual"
            self.settings.reflection_mode = mode
            save_settings(self.settings)
            return f"Reflection mode={mode} gespeichert."
        if raw in {"rule", "prompt", "promptregel"} and len(args) >= 2:
            self.settings.reflection_prompt_rule = str(args[1]).lower() in {"on", "true", "1", "ja"}
            save_settings(self.settings)
            return f"Reflection Prompt-Regel {'an' if self.settings.reflection_prompt_rule else 'aus'}."
        if raw == "last":
            return "\n".join(reflection_report_lines(get_last_reflection(), mode=self.settings.reflection_mode))

        return (
            "MAAT Reflection Befehle: `/maat reflection`, `/maat reflection on|off`, "
            "`/maat reflection banner on|off`, `/maat reflection mode auto|manual`, "
            "`/maat reflection rule on|off`, `/maat reflection last`."
        )

    def _maat_antihallu_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return antihallu_status_text(self.settings)

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.antihallu_enabled = raw == "on"
            save_settings(self.settings)
            return f"PLP Anti-Hallu {'aktiviert' if self.settings.antihallu_enabled else 'deaktiviert'}."
        if raw == "mode" and len(args) >= 2:
            self.settings.antihallu_mode = normalize_antihallu_mode(args[1])
            save_settings(self.settings)
            return f"PLP Anti-Hallu mode={self.settings.antihallu_mode} gespeichert."
        if raw == "symbolic" and len(args) >= 2:
            self.settings.antihallu_symbolic_lenient = str(args[1]).lower() in {"on", "true", "1", "ja"}
            save_settings(self.settings)
            return f"Symbolik/Gematria-Leniency {'an' if self.settings.antihallu_symbolic_lenient else 'aus'}."
        if raw == "banner" and len(args) >= 2:
            self.settings.antihallu_show_banner = str(args[1]).lower() in {"on", "true", "1", "ja"}
            save_settings(self.settings)
            return f"Anti-Hallu Banner {'an' if self.settings.antihallu_show_banner else 'aus'}."
        if raw in {"gap", "gaps", "fragen"} and len(args) >= 2:
            self.settings.antihallu_gap_questions = str(args[1]).lower() in {"on", "true", "1", "ja"}
            save_settings(self.settings)
            return f"Gap-Fragen {'an' if self.settings.antihallu_gap_questions else 'aus'}."
        if raw == "threshold" and len(args) >= 3:
            target = str(args[1]).lower()
            try:
                value = max(0.0, min(float(args[2]), 5.0))
            except (TypeError, ValueError):
                return "Usage: /maat antihallu threshold soften|strict <zahl>"
            if target == "soften":
                self.settings.antihallu_soften_threshold = value
            elif target == "strict":
                self.settings.antihallu_strict_threshold = value
            else:
                return "Usage: /maat antihallu threshold soften|strict <zahl>"
            save_settings(self.settings)
            return (
                "Anti-Hallu Thresholds gespeichert: "
                f"soften={self.settings.antihallu_soften_threshold:.2f} strict={self.settings.antihallu_strict_threshold:.2f}"
            )
        if raw == "last":
            return "\n".join(antihallu_report_lines(get_last_antihallu()))
        if raw == "eval":
            text = " ".join(args[1:]).strip()
            if not text:
                return "Usage: /maat antihallu eval <antwort>"
            result = evaluate_antihallu("", text, {}, self.settings)
            remember_antihallu(result)
            return "\n".join(antihallu_report_lines(result))
        if raw == "evalq":
            text = " ".join(args[1:]).strip()
            if "||" not in text:
                return "Usage: /maat antihallu evalq <frage> || <antwort>"
            question, answer = [part.strip() for part in text.split("||", 1)]
            result = evaluate_antihallu(question, answer, {}, self.settings)
            remember_antihallu(result)
            return "\n".join(antihallu_report_lines(result))

        return (
            "PLP Anti-Hallu Befehle: `/maat antihallu`, `/maat antihallu on|off`, "
            "`/maat antihallu mode warn|soften|strict`, `/maat antihallu symbolic on|off`, "
            "`/maat antihallu banner on|off`, `/maat antihallu gaps on|off`, "
            "`/maat antihallu threshold soften|strict <zahl>`, `/maat antihallu last`, "
            "`/maat antihallu eval <antwort>`, `/maat antihallu evalq <frage> || <antwort>`."
        )

    def _maat_identity_command(self, args: list[str], ctx: dict[str, Any]) -> str:
        if not args:
            return identity_status_text(self.settings)

        raw = str(args[0]).lower()
        if raw in {"on", "off"}:
            self.settings.identity_enabled = raw == "on"
            reset_identity_injection()
            save_settings(self.settings)
            return f"MAAT Identity {'aktiviert' if self.settings.identity_enabled else 'deaktiviert'}."
        if raw == "mode" and len(args) >= 2:
            self.settings.identity_mode = normalize_identity_mode(args[1])
            reset_identity_injection()
            save_settings(self.settings)
            return f"Identity mode={self.settings.identity_mode} gespeichert. Re-Injection beim nächsten Turn."
        if raw == "name" and len(args) >= 2:
            self.settings.identity_name = normalize_identity_name(" ".join(args[1:]))
            reset_identity_injection()
            save_settings(self.settings)
            return f"Identity name={self.settings.identity_name} gespeichert. Re-Injection beim nächsten Turn."
        if raw == "once" and len(args) >= 2:
            self.settings.identity_once = str(args[1]).lower() in {"on", "true", "1", "ja"}
            reset_identity_injection()
            save_settings(self.settings)
            return f"Identity once {'an' if self.settings.identity_once else 'aus'}."
        if raw == "reset":
            reset_identity_injection()
            return "Identity reset: wird beim nächsten Turn neu injiziert."
        if raw == "preview":
            return "```text\n" + build_identity_block(
                self.settings.identity_name,
                self.settings.identity_mode,
                self.settings.supermem_current_user,
            ) + "\n```"

        return (
            "MAAT Identity Befehle: `/maat identity`, `/maat identity on|off`, "
            "`/maat identity mode balanced|warm|deep|symbolic`, `/maat identity name <name>`, "
            "`/maat identity once on|off`, `/maat identity reset`, `/maat identity preview`."
        )

    def chat_loop(self) -> ChatLoop:
        return ChatLoop(self.database, self.plugins, self.commands, self.settings)

    def state(self) -> dict[str, Any]:
        return {
            "app": "MAAT Web Core",
            "settings": asdict(self.settings),
            "maat_thinking": level_status(self.settings.maat_thinking_level),
            "maat_spirit": spirit_status(self._spirit_settings()),
            "maat_style": {
                "status": style_status_text(self.settings),
            },
            "maat_core": {
                "enabled": bool(self.settings.maat_core_enabled),
                "mode": self.settings.maat_core_mode,
                "status": core_status_text(self.settings),
            },
            "maat_reality": reality_state(self.settings),
            "maat_balance": {
                "enabled": bool(self.settings.balance_enabled),
                "level": self.settings.balance_level,
                "debug": bool(self.settings.balance_debug),
                "once": bool(self.settings.balance_once),
                "self_reflect": bool(self.settings.balance_self_reflect),
                "dynamic": bool(self.settings.balance_dynamic),
                "context_weights": bool(self.settings.balance_context_weights),
                "counterpart_mode": bool(self.settings.balance_counterpart_mode),
                "status": balance_status_text(self.settings),
            },
            "maat_emotion": {
                "status": emotion_status_text(self.settings),
            },
            "super_memory": supermem_stats(self.database),
            "maat_engine": {
                "enabled": bool(self.settings.engine_enabled),
                "show_in_chat": bool(self.settings.engine_show_in_chat),
                "show_cci_debug": bool(self.settings.engine_show_cci_debug),
                "last_eval": get_last_eval(),
            },
            "maat_cci": {
                "enabled": bool(self.settings.advanced_cci_enabled),
                "show_debug": bool(self.settings.advanced_cci_show_debug),
                "kappa": float(self.settings.advanced_cci_kappa),
                "last_eval": get_last_advanced_cci(),
            },
            "maat_adaptive_learning": adaptive_learning_stats(self.database, self.settings),
            "maat_feedback_tool": feedback_status(self.settings),
            "maat_context_optimizer": {"status": context_optimizer_status_text(self.settings)},
            "maat_chat_search": {"status": chat_search_status_text(self.database, self.settings)},
            "maat_project_memory": project_state(self.database, self.settings),
            "maat_file_builder": file_builder_state(self.settings),
            "system_scan": system_scan(self.settings),
            "maat_claim_guard": {
                "enabled": bool(self.settings.claim_guard_enabled),
                "mode": self.settings.claim_guard_mode,
                "after_output": bool(self.settings.claim_guard_after_output),
                "banner": bool(self.settings.claim_guard_show_banner),
                "status": claim_status_text(self.settings),
                "last_eval": get_last_claim(),
            },
            "maat_rewrite": {
                "enabled": bool(self.settings.rewrite_enabled),
                "mode": self.settings.rewrite_mode,
                "banner": bool(self.settings.rewrite_show_banner),
                "trim": bool(self.settings.rewrite_trim_outputs),
                "field_weak": float(self.settings.rewrite_field_weak),
                "field_strong": float(self.settings.rewrite_field_strong),
                "r_min": float(self.settings.rewrite_r_min),
                "status": rewrite_status_text(self.settings),
                "last_eval": get_last_rewrite(),
            },
            "maat_reflection": {
                "enabled": bool(self.settings.reflection_enabled),
                "banner": bool(self.settings.reflection_banner),
                "mode": self.settings.reflection_mode,
                "prompt_rule": bool(self.settings.reflection_prompt_rule),
                "status": reflection_status_text(self.settings),
                "last_eval": get_last_reflection(),
            },
            "maat_antihallu": {
                "enabled": bool(self.settings.antihallu_enabled),
                "mode": self.settings.antihallu_mode,
                "banner": bool(self.settings.antihallu_show_banner),
                "gap_questions": bool(self.settings.antihallu_gap_questions),
                "symbolic_lenient": bool(self.settings.antihallu_symbolic_lenient),
                "soften_threshold": float(self.settings.antihallu_soften_threshold),
                "strict_threshold": float(self.settings.antihallu_strict_threshold),
                "status": antihallu_status_text(self.settings),
                "last_eval": get_last_antihallu(),
            },
            "maat_identity": {
                "enabled": bool(self.settings.identity_enabled),
                "name": self.settings.identity_name,
                "mode": self.settings.identity_mode,
                "once": bool(self.settings.identity_once),
                "status": identity_status_text(self.settings),
            },
            "offline_wiki": {
                "status": offline_wiki_status_text(self.settings),
            },
            "plugins": self.plugins.info(),
            "plugin_errors": self.plugins.errors,
            "database": self.database.stats(),
        }

    def _loader_signature(self) -> tuple[Any, ...]:
        return (
            str(self.settings.model_adapter or ""),
            str(self.settings.model_name or ""),
            str(self.settings.llama_model_path or ""),
            int(self.settings.llama_n_ctx),
            int(self.settings.llama_n_threads),
            int(self.settings.llama_n_gpu_layers),
            str(self.settings.loader_tuning_mode or "manual"),
            bool(getattr(self.settings, "max_tokens_from_ctx", False)),
        )

    def update_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        old_loader_signature = self._loader_signature()
        identity_keys = {"identity_enabled", "identity_name", "identity_mode", "identity_once"}
        identity_changed = any(key in payload and getattr(self.settings, key, None) != payload.get(key) for key in identity_keys)
        core_keys = {"maat_core_enabled", "maat_core_mode"}
        core_changed = any(key in payload and getattr(self.settings, key, None) != payload.get(key) for key in core_keys)
        balance_keys = {
            "balance_enabled",
            "balance_level",
            "balance_once",
            "balance_self_reflect",
            "balance_dynamic",
            "balance_context_weights",
            "balance_counterpart_mode",
        }
        balance_changed = any(key in payload and getattr(self.settings, key, None) != payload.get(key) for key in balance_keys)
        for key, value in payload.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.settings.maat_thinking_level = normalize_level(self.settings.maat_thinking_level)
        self.settings.loader_tuning_mode = (
            "auto" if str(getattr(self.settings, "loader_tuning_mode", "manual")).lower() == "auto" else "manual"
        )
        try:
            self.settings.llama_n_ctx = max(512, min(131072, int(self.settings.llama_n_ctx)))
        except (TypeError, ValueError):
            self.settings.llama_n_ctx = 4096
        try:
            self.settings.llama_n_threads = max(1, min(128, int(self.settings.llama_n_threads)))
        except (TypeError, ValueError):
            self.settings.llama_n_threads = 8
        try:
            self.settings.llama_n_gpu_layers = max(0, min(999, int(self.settings.llama_n_gpu_layers)))
        except (TypeError, ValueError):
            self.settings.llama_n_gpu_layers = 0
        if identity_changed:
            self.settings.identity_name = normalize_identity_name(self.settings.identity_name)
            self.settings.identity_mode = normalize_identity_mode(self.settings.identity_mode)
            reset_identity_injection()
        if core_changed:
            self.settings.maat_core_mode = normalize_core_mode(self.settings.maat_core_mode)
        if balance_changed:
            self.settings.balance_level = normalize_balance_level(self.settings.balance_level)
            reset_balance_injection()
        self.settings.claim_guard_mode = normalize_claim_mode(self.settings.claim_guard_mode)
        self.settings.rewrite_mode = normalize_rewrite_mode(self.settings.rewrite_mode)
        try:
            self.settings.adaptive_learning_per_turn = max(0, min(2, int(self.settings.adaptive_learning_per_turn)))
        except (TypeError, ValueError):
            self.settings.adaptive_learning_per_turn = 2
        try:
            self.settings.adaptive_learning_exploration_rate = max(
                0.0,
                min(1.0, float(self.settings.adaptive_learning_exploration_rate)),
            )
        except (TypeError, ValueError):
            self.settings.adaptive_learning_exploration_rate = 0.25
        try:
            self.settings.adaptive_learning_user_bonus = max(
                0.0,
                min(0.6, float(self.settings.adaptive_learning_user_bonus)),
            )
        except (TypeError, ValueError):
            self.settings.adaptive_learning_user_bonus = 0.20
        try:
            self.settings.feedback_history_limit = max(5, min(100, int(self.settings.feedback_history_limit)))
        except (TypeError, ValueError):
            self.settings.feedback_history_limit = 25
        try:
            self.settings.feedback_self_learning_per_report = max(
                0,
                min(5, int(self.settings.feedback_self_learning_per_report)),
            )
        except (TypeError, ValueError):
            self.settings.feedback_self_learning_per_report = 2
        for attr, default in {
            "feedback_warn_below_b": 0.60,
            "feedback_warn_below_r": 0.75,
            "feedback_warn_below_h": 0.65,
        }.items():
            try:
                setattr(self.settings, attr, max(0.0, min(1.0, float(getattr(self.settings, attr)))))
            except (TypeError, ValueError):
                setattr(self.settings, attr, default)
        for attr, default, minimum, maximum in [
            ("supermem_top_k", 5, 1, 20),
            ("supermem_person_top_k", 4, 0, 10),
            ("supermem_person_graph_top_k", 2, 0, 10),
            ("supermem_max_memories", 1000, 100, 20000),
            ("supermem_dream_hours", 24, 1, 168),
            ("supermem_archive_after_days", 30, 7, 3650),
        ]:
            try:
                setattr(self.settings, attr, max(minimum, min(maximum, int(getattr(self.settings, attr)))))
            except (TypeError, ValueError):
                setattr(self.settings, attr, default)
        try:
            self.settings.supermem_min_score = max(0.0, min(1.0, float(self.settings.supermem_min_score)))
        except (TypeError, ValueError):
            self.settings.supermem_min_score = 0.15
        try:
            self.settings.supermem_user_memory_bonus = max(0.0, min(0.4, float(self.settings.supermem_user_memory_bonus)))
        except (TypeError, ValueError):
            self.settings.supermem_user_memory_bonus = 0.12
        try:
            self.settings.project_memory_top_k = max(0, min(5, int(self.settings.project_memory_top_k)))
        except (TypeError, ValueError):
            self.settings.project_memory_top_k = 2
        try:
            self.settings.project_memory_max_chars = max(800, min(8000, int(self.settings.project_memory_max_chars)))
        except (TypeError, ValueError):
            self.settings.project_memory_max_chars = 2600
        try:
            self.settings.file_builder_preview_chars = max(500, min(20000, int(self.settings.file_builder_preview_chars)))
        except (TypeError, ValueError):
            self.settings.file_builder_preview_chars = 5000
        try:
            self.settings.file_builder_max_bytes = max(1024, min(20_000_000, int(self.settings.file_builder_max_bytes)))
        except (TypeError, ValueError):
            self.settings.file_builder_max_bytes = 2_000_000
        try:
            self.settings.file_builder_tex_timeout = max(5, min(180, int(self.settings.file_builder_tex_timeout)))
        except (TypeError, ValueError):
            self.settings.file_builder_tex_timeout = 45
        try:
            self.settings.file_builder_python_timeout = max(1, min(60, int(self.settings.file_builder_python_timeout)))
        except (TypeError, ValueError):
            self.settings.file_builder_python_timeout = 8
        try:
            self.settings.file_builder_feedback_chars = max(500, min(20000, int(self.settings.file_builder_feedback_chars)))
        except (TypeError, ValueError):
            self.settings.file_builder_feedback_chars = 6000
        for attr, default, minimum, maximum in [
            ("chat_compressor_trigger_turns", 10, 1, 200),
            ("chat_compressor_keep_recent_turns", 6, 1, 50),
            ("chat_compressor_context_threshold_tokens", 12000, 512, 131072),
            ("chat_compressor_max_summary_chars", 3500, 700, 20000),
            ("context_optimizer_max_memory_items", 6, 1, 20),
            ("context_optimizer_max_memory_chars", 2600, 400, 12000),
            ("chat_search_max_results", 6, 1, 30),
            ("chat_search_scan_interval", 45, 1, 3600),
        ]:
            try:
                setattr(self.settings, attr, max(minimum, min(maximum, int(getattr(self.settings, attr)))))
            except (TypeError, ValueError):
                setattr(self.settings, attr, default)
        new_loader_signature = self._loader_signature()
        if old_loader_signature != new_loader_signature and (
            old_loader_signature[0] == "llama_cpp_direct" or new_loader_signature[0] == "llama_cpp_direct"
        ):
            clear_model_cache("settings/model switch")
        save_settings(self.settings)
        return {
            "settings": asdict(self.settings),
            "offline_wiki": {"status": offline_wiki_status_text(self.settings)},
            "maat_identity": {"status": identity_status_text(self.settings)},
            "maat_antihallu": {"status": antihallu_status_text(self.settings)},
            "maat_core": {"status": core_status_text(self.settings)},
            "maat_reality": reality_state(self.settings),
            "maat_balance": {"status": balance_status_text(self.settings)},
            "maat_adaptive_learning": adaptive_learning_stats(self.database, self.settings),
            "maat_feedback_tool": feedback_status(self.settings),
            "maat_context_optimizer": {"status": context_optimizer_status_text(self.settings)},
            "maat_chat_search": {"status": chat_search_status_text(self.database, self.settings)},
            "maat_project_memory": project_state(self.database, self.settings),
            "maat_file_builder": file_builder_state(self.settings),
            "system_scan": system_scan(self.settings),
            "maat_claim_guard": {"status": claim_status_text(self.settings)},
            "maat_rewrite": {"status": rewrite_status_text(self.settings)},
        }

    def projects_payload(self, selected: str = "", query: str = "") -> dict[str, Any]:
        state = project_state(self.database, self.settings, selected)
        markdown_target = selected or str((state.get("selected") or {}).get("id") or "")
        if query.strip():
            hits = project_search(self.database, query, 5)
            return {
                **state,
                "search": {"query": query, "hits": hits},
                "markdown": format_project_markdown(self.database, markdown_target),
            }
        return {
            **state,
            "markdown": format_project_markdown(self.database, markdown_target),
        }

    def docs_payload(self, selected: str = "") -> dict[str, Any]:
        return file_builder_state(self.settings, selected=selected)

    def person_graph_payload(self, source_user: str = "") -> dict[str, Any]:
        return person_graph_state(self.database, self.settings, source_user or self.settings.supermem_current_user)

    def save_person_graph(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            state = person_graph_upsert(self.database, self.settings, payload)
            save_settings(self.settings)
            return {"ok": True, **state, "settings": asdict(self.settings)}
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                **self.person_graph_payload(str(payload.get("source_user") or "")),
                "settings": asdict(self.settings),
            }

    def delete_person_graph(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            state = person_graph_delete(self.database, self.settings, payload)
            return {"ok": True, **state, "settings": asdict(self.settings)}
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                **self.person_graph_payload(str(payload.get("source_user") or "")),
                "settings": asdict(self.settings),
            }

    def run_super_memory_dream(self) -> dict[str, Any]:
        try:
            result = run_memory_dreaming(self.database, self.settings)
            return {"ok": True, "result": result, "super_memory": supermem_stats(self.database), "settings": asdict(self.settings)}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "super_memory": supermem_stats(self.database), "settings": asdict(self.settings)}

    def system_scan_payload(self) -> dict[str, Any]:
        scan = system_scan(self.settings)
        self.settings.loader_scan_result = scan
        save_settings(self.settings)
        return {"ok": True, "system_scan": scan, "settings": asdict(self.settings)}

    def apply_system_scan(self) -> dict[str, Any]:
        scan = apply_auto_loader_settings(self.settings)
        save_settings(self.settings)
        return {"ok": True, "system_scan": scan, "settings": asdict(self.settings)}

    def restart_server(self) -> dict[str, Any]:
        save_settings(self.settings)
        executable = sys.executable
        argv = [sys.executable, *sys.argv]

        def restart_later() -> None:
            time.sleep(0.45)
            print("[MAAT Web Core] Neustart angefordert. Prozess wird ersetzt...", flush=True)
            os.execv(executable, argv)

        threading.Thread(target=restart_later, name="maat-web-core-restart", daemon=True).start()
        return {"ok": True, "message": "MAAT Web Core startet neu.", "argv": argv}

    def save_doc(self, payload: dict[str, Any]) -> dict[str, Any]:
        return save_manual_doc(self.settings, payload)

    def run_doc_python(self, payload: dict[str, Any]) -> dict[str, Any]:
        return run_python_doc(self.settings, payload)

    def delete_doc(self, payload: dict[str, Any]) -> dict[str, Any]:
        return delete_builder_doc(self.settings, payload)

    def open_doc(self, payload: dict[str, Any]) -> dict[str, Any]:
        return open_builder_doc(self.settings, payload)

    def save_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            project = upsert_project(self.database, payload)
            return {"ok": True, "project": project, **self.projects_payload(str(project.get("id") or ""))}
        except Exception as exc:
            return {"ok": False, "error": str(exc), **self.projects_payload(str(payload.get("id") or ""))}

    def add_project_child(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_name = str(payload.get("project") or payload.get("project_id") or "").strip()
        kind = str(payload.get("kind") or "").strip()
        try:
            if kind == "formula":
                project_add_formula(
                    self.database,
                    project_name,
                    str(payload.get("name") or ""),
                    str(payload.get("formula") or ""),
                    str(payload.get("description") or ""),
                )
            elif kind == "paper":
                project_add_paper(
                    self.database,
                    project_name,
                    str(payload.get("title") or ""),
                    str(payload.get("ref") or ""),
                    str(payload.get("notes") or ""),
                )
            elif kind == "entry":
                project_add_entry(
                    self.database,
                    project_name,
                    str(payload.get("entry_type") or "insight"),
                    str(payload.get("text") or ""),
                    payload.get("tags") or "",
                )
            else:
                raise ValueError("Unbekannter Typ.")
            return {"ok": True, **self.projects_payload(project_name)}
        except Exception as exc:
            return {"ok": False, "error": str(exc), **self.projects_payload(project_name)}

    def delete_project_child(self, payload: dict[str, Any]) -> dict[str, Any]:
        kind = str(payload.get("kind") or "")
        child_id = str(payload.get("id") or "")
        selected = str(payload.get("project") or payload.get("project_id") or "")
        try:
            ok = project_delete_child(self.database, kind, child_id)
            return {"ok": ok, **self.projects_payload(selected)}
        except Exception as exc:
            return {"ok": False, "error": str(exc), **self.projects_payload(selected)}

    def rename_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            chat_id = int(payload.get("chat_id"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "Ungültige Chat-ID"}
        ok = self.database.rename_chat(chat_id, str(payload.get("title") or ""))
        return {"ok": ok, "chat": self.database.chat(chat_id)}

    def delete_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            chat_id = int(payload.get("chat_id"))
        except (TypeError, ValueError):
            return {"ok": False, "error": "Ungültige Chat-ID"}
        ok = self.database.delete_chat(chat_id)
        return {"ok": ok, "deleted_chat_id": chat_id}

    def speak(self, payload: dict[str, Any]) -> dict[str, Any]:
        def speech_command(text: str) -> tuple[list[str], str] | None:
            say_path = shutil.which("say")
            if say_path:
                return [say_path, text], "say"

            spd_say_path = shutil.which("spd-say")
            if spd_say_path:
                return [spd_say_path, "-w", text], "spd-say"

            espeak_ng_path = shutil.which("espeak-ng")
            if espeak_ng_path:
                return [espeak_ng_path, "-v", "de", text], "espeak-ng"

            espeak_path = shutil.which("espeak")
            if espeak_path:
                return [espeak_path, "-v", "de", text], "espeak"

            return None

        def stop_current() -> None:
            if self.speech_process and self.speech_process.poll() is None:
                self.speech_process.terminate()
                try:
                    self.speech_process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    self.speech_process.kill()
            self.speech_process = None

        action = str(payload.get("action") or "speak").lower()
        if self.speech_process and self.speech_process.poll() is not None:
            self.speech_process = None

        if action == "stop":
            stop_current()
            return {"ok": True, "status": "stopped"}

        text = str(payload.get("text") or "")
        text = visible_message_text(text)
        text = re.sub(
            r"```(?:text)?\s*H=\d+(?:\.\d+)?\s+B=\d+(?:\.\d+)?\s+S=\d+(?:\.\d+)?\s+V=\d+(?:\.\d+)?\s+R=\d+(?:\.\d+)?[\s\S]*?```",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^\s*H=\d+(?:\.\d+)?\s+B=\d+(?:\.\d+)?\s+S=\d+(?:\.\d+)?\s+V=\d+(?:\.\d+)?\s+R=\d+(?:\.\d+)?\s+→\s+Stability=\d+(?:\.\d+)?\s*$",
            "",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        text = re.sub(r"^\s*Maat Value=\d+(?:\.\d+)?\s*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r"^\s*Fokusfelder:.*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r"^\s*B_dynamic=.*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r"^\s*CCI(?:_runtime)?=.*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r"```[\s\S]*?```", " ", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"[*_#>~]+", "", text)
        text = re.sub(r"https?://\S+", " Link ausgelassen. ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return {"ok": False, "error": "Kein lesbarer Text gefunden."}
        if len(text) > 6000:
            text = text[:6000].rsplit(" ", 1)[0] + " ..."

        command = speech_command(text)
        if not command:
            return {
                "ok": False,
                "error": "Kein TTS-Befehl gefunden. Installiere z.B. `speech-dispatcher`/`spd-say` oder `espeak-ng`.",
            }
        argv, engine = command

        stop_current()

        try:
            self.speech_process = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "status": "speaking", "engine": engine, "chars": len(text)}

    def gguf_models(self) -> dict[str, Any]:
        roots: list[dict[str, Any]] = []
        models: list[dict[str, Any]] = []
        seen: set[str] = set()

        for root in gguf_model_dirs(self.settings.gguf_model_dirs_custom):
            exists = root.exists() and root.is_dir()
            roots.append({"path": str(root), "exists": exists})
            if not exists:
                continue
            try:
                matches = sorted(root.rglob("*.gguf"), key=lambda item: item.name.lower())
            except Exception as exc:
                roots[-1]["error"] = str(exc)
                continue

            for path in matches[:1000]:
                key = str(path)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    size = path.stat().st_size
                except OSError:
                    size = None
                models.append(
                    {
                        "name": path.name,
                        "path": key,
                        "directory": str(path.parent),
                        "size": size,
                    }
                )

        models.sort(key=lambda item: (item["name"].lower(), item["path"].lower()))
        return {"models": models, "roots": roots}

    def command_items(self) -> list[dict[str, str]]:
        items = []
        for name, (_, description) in sorted(self.commands.commands.items()):
            aliases = sorted(alias for alias, target in self.commands.aliases.items() if target == name)
            items.append(
                {
                    "name": name,
                    "description": description,
                    "aliases": ", ".join(aliases),
                }
            )
        return items

    def system_status_markdown(self) -> str:
        plugins = self.plugins.info()
        memory = supermem_stats(self.database)
        learning = adaptive_learning_stats(self.database, self.settings)
        feedback = feedback_status(self.settings)
        projects = project_state(self.database, self.settings)
        layers = memory.get("layers") or {}
        lines = [
            "# MAAT System Status",
            "",
            f"- Adapter: `{self.settings.model_adapter}`",
            f"- Modell: `{self.settings.model_name}`",
            f"- Super Memory: `{'on' if self.settings.supermem_enabled else 'off'}` · Saves `{sum(int(value or 0) for value in layers.values())}` · Graph `{memory.get('person_graph', 0)}`",
            f"- MAAT Value Core: `{'on' if self.settings.maat_core_enabled else 'off'}` · mode `{self.settings.maat_core_mode}`",
            f"- MAAT Reality: `{'on' if self.settings.reality_enabled else 'off'}` · {reality_state(self.settings).get('weekday')} `{reality_state(self.settings).get('date')}` `{reality_state(self.settings).get('time')}`",
            f"- MAAT Engine: `{'on' if self.settings.engine_enabled else 'off'}`",
            f"- Advanced CCI: `{'on' if self.settings.advanced_cci_enabled else 'off'}`",
            f"- Adaptive Learning: `{'on' if self.settings.adaptive_learning_enabled else 'off'}` · inject `{'on' if self.settings.adaptive_learning_inject else 'off'}` · Lessons `{learning.get('active', 0)}`",
            f"- Feedback Tool: `{'on' if self.settings.feedback_enabled else 'off'}` · Reports `{feedback.get('history', 0)}` · Self-Learning `{'on' if self.settings.feedback_self_learning_enabled else 'off'}`",
            f"- ChatSearch: `{'on' if self.settings.chat_search_enabled else 'off'}` · Auto-Index `{'on' if self.settings.chat_search_auto_index else 'off'}`",
            f"- Project Memory: `{'on' if self.settings.project_memory_enabled else 'off'}` · Projekte `{len(projects.get('projects') or [])}` · Top-K `{self.settings.project_memory_top_k}`",
            f"- Docs/File Builder: `{'on' if self.settings.file_builder_enabled else 'off'}` · inject `{'on' if self.settings.file_builder_inject_instructions else 'off'}`",
            f"- Claim Guard: `{'on' if self.settings.claim_guard_enabled else 'off'}` · mode `{self.settings.claim_guard_mode}` · output `{'on' if self.settings.claim_guard_after_output else 'off'}`",
            f"- Rewrite Loop: `{'on' if self.settings.rewrite_enabled else 'off'}` · mode `{self.settings.rewrite_mode}` · trim `{'on' if self.settings.rewrite_trim_outputs else 'off'}`",
            f"- Reflection: `{'on' if self.settings.reflection_enabled else 'off'}`",
            f"- Anti-Hallu: `{'on' if self.settings.antihallu_enabled else 'off'}` · mode `{self.settings.antihallu_mode}`",
            f"- Offline Wiki: `{'on' if self.settings.offline_wiki_enabled else 'off'}`",
            f"- Plugins: `{len(plugins)}`",
        ]
        return "\n".join(lines)

    def help_markdown(self) -> str:
        lines = [
            "# MAAT Help",
            "",
            "Router-basierte Hilfe: diese Liste kommt direkt aus dem aktiven CommandRouter.",
            "",
            "## Commands",
        ]
        for item in self.command_items():
            alias_text = f" · Aliase: `{item['aliases']}`" if item["aliases"] else ""
            desc = item["description"] or "kein Beschreibungstext"
            lines.append(f"- `{item['name']}` — {desc}{alias_text}")

        plugins = self.plugins.info()
        lines.extend(
            [
                "",
                "## MAAT Kurzbefehle",
                "- `/maat help` — diese Hilfe",
                "- `/maat status` — Systemstatus",
                "- `/maat memory recall <suchtext>` · `/maat memory selfsave on|off` — Erinnerungen suchen oder KI-SelfSave steuern",
                "- `/maat graph` — Personen-Graph anzeigen",
                "- `/maat mode` · `/maat mode test <text>` — erkannten Antwortmodus anzeigen, ohne Prompt-Injection",
                "- `/maat lessons` · `/maat lessons add <category>|<type>|<lesson>` — adaptive Denkregeln anzeigen oder speichern",
                "- `/maat feedback` · `/maat feedback test <text>` — letzte Antwort diagnostizieren oder Text testen",
                "- `/maat search <query>` · `/maat search rebuild` · `/maat search stats` — Web-Core- und textgen-Chatarchiv durchsuchen",
                "- `/maat project` · `/maat project add <name>|<tags>|<beschreibung>` — Forschungsprojekte, Formeln und Papers verwalten",
                "- `/maat docs` · `/maat docs last` — erzeugte Docs/File-Builder-Dateien anzeigen",
                "- `/maat why` — aktive Lessons/Hints des letzten Prompts anzeigen",
                "- `/maat core mode light|standard|strict` — MAAT Value Core steuern",
                "- `/maat reality` · `/maat time` · `/maat date` — Live-Datum/Uhrzeit und Reality-Layer",
                "- `/maat balance preview <text>` — Balance-Injection testen",
                "- `/maat claim test <text>` — starke Behauptungen und Claim-Risiko testen",
                "- `/maat rewrite` — finalen Rewrite-Cleanup steuern",
                "- `/maat engine eval <text>` — H/B/S/V/R testen",
                "- `/maat antihallu evalq <frage> || <antwort>` — Hallu-Risiko testen",
                "- `/maat wiki <begriff>` — Offline-Wiki abfragen",
                "",
                "## Geladene Plugins",
            ]
        )
        if plugins:
            for plugin in plugins:
                commands = ", ".join(plugin.get("commands") or []) or "keine Commands"
                lines.append(f"- `{plugin.get('id')}` · {plugin.get('type')} · {commands}")
        else:
            lines.append("- keine")
        return "\n".join(lines)

    def help_payload(self) -> dict[str, Any]:
        return {
            "markdown": self.help_markdown(),
            "status": self.system_status_markdown(),
            "commands": self.command_items(),
            "plugins": self.plugins.info(),
        }


class MaatRequestHandler(BaseHTTPRequestHandler):
    runtime: WebCoreRuntime
    auth: tuple[str, str] | None = None

    server_version = "MAATWebCore/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path_only = parsed.path
        if path_only == "/access-denied":
            self._access_denied_page()
            return
        if not self._check_auth():
            return
        if path_only == "/":
            self._serve_file(STATIC_DIR / "index.html")
            return
        if path_only.startswith("/static/"):
            rel = path_only.removeprefix("/static/")
            self._serve_file(STATIC_DIR / rel)
            return
        if path_only == "/api/state":
            self._json(self.runtime.state())
            return
        if path_only == "/api/help":
            self._json(self.runtime.help_payload())
            return
        if path_only == "/api/projects":
            query = parse_qs(parsed.query)
            selected = (query.get("selected") or [""])[0]
            search = (query.get("q") or [""])[0]
            self._json(self.runtime.projects_payload(selected, search))
            return
        if path_only == "/api/docs":
            query = parse_qs(parsed.query)
            selected = (query.get("selected") or [""])[0]
            self._json(self.runtime.docs_payload(selected))
            return
        if path_only == "/api/docs/download":
            query = parse_qs(parsed.query)
            doc_id = (query.get("id") or [""])[0]
            self._serve_doc_download(doc_id)
            return
        if path_only == "/api/chats":
            self._json({"chats": self.runtime.database.list_chats()})
            return
        if path_only == "/api/chat":
            query = parse_qs(parsed.query)
            try:
                chat_id = int((query.get("chat_id") or [""])[0])
            except (TypeError, ValueError):
                self._json({"chat": None, "messages": []})
                return
            self._json(
                {
                    "chat": self.runtime.database.chat(chat_id),
                    "messages": self.runtime.database.chat_messages(chat_id),
                }
            )
            return
        if path_only == "/api/gguf-models":
            self._json(self.runtime.gguf_models())
            return
        if path_only == "/api/system-scan":
            self._json(self.runtime.system_scan_payload())
            return
        if path_only == "/api/super-memory/person-graph":
            query = parse_qs(parsed.query)
            source_user = (query.get("source_user") or [""])[0]
            self._json(self.runtime.person_graph_payload(source_user))
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        if not self._check_auth():
            return
        if self.path == "/api/settings":
            payload = self._read_json()
            self._json(self.runtime.update_settings(payload))
            return
        if self.path == "/api/system-scan/apply":
            self._json(self.runtime.apply_system_scan())
            return
        if self.path == "/api/restart":
            self._json(self.runtime.restart_server())
            return
        if self.path == "/api/projects/save":
            payload = self._read_json()
            self._json(self.runtime.save_project(payload))
            return
        if self.path == "/api/projects/child":
            payload = self._read_json()
            self._json(self.runtime.add_project_child(payload))
            return
        if self.path == "/api/projects/delete-child":
            payload = self._read_json()
            self._json(self.runtime.delete_project_child(payload))
            return
        if self.path == "/api/docs/save":
            payload = self._read_json()
            self._json(self.runtime.save_doc(payload))
            return
        if self.path == "/api/docs/run-python":
            payload = self._read_json()
            self._json(self.runtime.run_doc_python(payload))
            return
        if self.path == "/api/docs/delete":
            payload = self._read_json()
            self._json(self.runtime.delete_doc(payload))
            return
        if self.path == "/api/docs/open":
            payload = self._read_json()
            self._json(self.runtime.open_doc(payload))
            return
        if self.path == "/api/super-memory/person-graph/save":
            payload = self._read_json()
            self._json(self.runtime.save_person_graph(payload))
            return
        if self.path == "/api/super-memory/person-graph/delete":
            payload = self._read_json()
            self._json(self.runtime.delete_person_graph(payload))
            return
        if self.path == "/api/super-memory/dream":
            self._json(self.runtime.run_super_memory_dream())
            return
        if self.path == "/api/chat/rename":
            payload = self._read_json()
            self._json(self.runtime.rename_chat(payload))
            return
        if self.path == "/api/chat/delete":
            payload = self._read_json()
            self._json(self.runtime.delete_chat(payload))
            return
        if self.path == "/api/speak":
            payload = self._read_json()
            self._json(self.runtime.speak(payload))
            return
        if self.path == "/api/chat/stream":
            payload = self._read_json()
            self._stream_chat(payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _check_auth(self) -> bool:
        credentials = self.auth
        if credentials is None:
            return True

        expected_user, expected_password = credentials
        raw = self.headers.get("Authorization", "")
        prefix = "Basic "
        if not raw.startswith(prefix):
            self._auth_required()
            return False

        try:
            decoded = base64.b64decode(raw[len(prefix) :].strip(), validate=True).decode("utf-8")
        except Exception:
            self._auth_denied_redirect()
            return False

        user, sep, password = decoded.partition(":")
        if not sep:
            self._auth_denied_redirect()
            return False

        if hmac.compare_digest(user, expected_user) and hmac.compare_digest(password, expected_password):
            return True

        self._auth_denied_redirect()
        return False

    def _auth_required(self) -> None:
        body = ACCESS_DENIED_HTML.encode("utf-8")
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="MAAT Web Core", charset="UTF-8"')
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_no_store_headers()
        self.end_headers()
        self.wfile.write(body)

    def _auth_denied_redirect(self) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/access-denied")
        self._send_no_store_headers()
        self.end_headers()

    def _access_denied_page(self) -> None:
        body = ACCESS_DENIED_HTML.encode("utf-8")
        self.send_response(HTTPStatus.FORBIDDEN)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_no_store_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_no_store_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self._send_no_store_headers()
        self.end_headers()
        self.wfile.write(data)

    def _serve_doc_download(self, doc_id: str) -> None:
        path = doc_path_by_id(doc_id)
        if path is None or not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Doc not found")
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self._send_no_store_headers()
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _json(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self._send_no_store_headers()
        self.end_headers()
        self.wfile.write(data)

    def _stream_chat(self, payload: dict[str, Any]) -> None:
        message = str(payload.get("message") or "")
        chat_id = payload.get("chat_id")
        try:
            chat_id = int(chat_id) if chat_id is not None else None
        except (TypeError, ValueError):
            chat_id = None

        preview = " ".join(visible_message_text(message).split())[:80]
        print(f"[MAAT Web Core] Stream start chat_id={chat_id} message={preview!r}", flush=True)

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.close_connection = True

        def write_sse(event: str, payload: dict[str, Any]) -> bool:
            try:
                data = f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                self.wfile.write(data.encode("utf-8"))
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError, OSError):
                return False

        async def run_stream() -> None:
            try:
                async for event in self.runtime.chat_loop().stream(message, chat_id):
                    try:
                        self.wfile.write(event.encode("utf-8"))
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        break
            except Exception as exc:
                print("[MAAT Web Core] Stream error:", repr(exc), flush=True)
                traceback.print_exc()
                write_sse(
                    "replace",
                    {
                        "content": (
                            "Fehler im lokalen MAAT-Stream.\n\n"
                            f"`{type(exc).__name__}: {exc}`"
                        ),
                        "error": True,
                    },
                )
                write_sse("done", {"chat_id": chat_id})

        try:
            asyncio.run(run_stream())
        except Exception as exc:
            print("[MAAT Web Core] Stream runtime error:", repr(exc), flush=True)
            traceback.print_exc()
        finally:
            print(f"[MAAT Web Core] Stream end chat_id={chat_id}", flush=True)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[MAAT Web Core] {self.address_string()} - {fmt % args}")


def run_server(host: str = "127.0.0.1", port: int = 8787) -> None:
    runtime = WebCoreRuntime()
    MaatRequestHandler.runtime = runtime
    MaatRequestHandler.auth = auth_credentials()
    server = ThreadingHTTPServer((host, port), MaatRequestHandler)
    display_url = f"http://{host}:{port}"
    if host in {"0.0.0.0", "::"}:
        display_url = f"http://<LAN-IP>:{port}"
    print(f"MAAT Web Core läuft auf {display_url}")
    if host in {"0.0.0.0", "::"}:
        print("LAN-Modus: aktiv · IP-Adresse des Rechners im lokalen Netzwerk verwenden")
    if MaatRequestHandler.auth:
        print(f"Basic Auth: aktiv · user={MaatRequestHandler.auth[0]!r}")
    else:
        print("Basic Auth: aus · MAAT_WEB_AUTH_USER/PASSWORD nicht gesetzt")
    print(f"Plugins: {', '.join(plugin['id'] for plugin in runtime.plugins.info()) or 'keine'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMAAT Web Core beendet.")
    finally:
        server.server_close()
