from __future__ import annotations

import asyncio
import contextlib
import json
import re
import time
from collections.abc import AsyncIterator
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .commands import CommandRouter
from .config import RuntimeSettings
from .database import Database
from .maat_balance import balance_state, build_balance_prompt, strip_balance_tags
from .maat_chat_compressor import (
    build_chat_digest,
    compress_history_for_prompt,
    report_lines as compressor_report_lines,
)
from .maat_chat_search import direct_chat_search_answer
from .maat_adaptive_learning import build_active_lessons_block, record_silent_feedback
from .maat_claim_guard import (
    apply_claim_guard_output,
    build_claim_prompt,
    report_lines as claim_report_lines,
    strip_claim_guard_tags,
)
from .maat_context_optimizer import (
    optimize_context,
    report_lines as context_optimizer_report_lines,
)
from .maat_feedback_tool import record_feedback as record_feedback_report, score_line as feedback_score_line
from .maat_file_builder import (
    build_file_builder_feedback_prompt,
    build_file_builder_prompt,
    process_file_builder_output,
    strip_file_builder_chat_cards,
    strip_file_builder_tags,
)
from .maat_emotion import build_emotion_prompt
from .maat_cci_engine import compute_advanced_cci, remember_advanced_cci, report_lines as advanced_cci_report_lines
from .maat_engine import debug_lines, evaluate_text, get_last_eval, remember_eval
from .maat_identity import build_identity_prompt, strip_identity_tags
from .maat_offline_wiki import build_wiki_prompt
from .maat_project_memory import build_project_prompt
from .maat_plp_anti_hallu import apply_antihallu_guard, build_antihallu_prompt
from .maat_reality_layer import build_reality_prompt, direct_reality_answer, strip_reality_tags
from .maat_reflection import apply_reflection_banner, build_reflection_prompt
from .maat_rewrite_loop import apply_rewrite_loop, report_lines as rewrite_report_lines
from .maat_spirit import SpiritSettings, build_spirit_prompt_block
from .maat_style import build_style_prompt, strip_routine_opening
from .maat_super_memory import build_memory_prompt, process_turn_memory
from .maat_thinking import build_prompt_block
from .maat_value_core import build_core_prompt, strip_core_tags
from .models.echo import EchoAdapter
from .models.llama_cpp_direct import LlamaCppDirectAdapter, normalize_options_for_model
from .models.openai_compat import OpenAICompatAdapter
from .plugins import PluginManager
from .system_scan import effective_loader_values


def sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


FREE_THINKING_START_RE = re.compile(
    r"^\s*(?:"
    r"here(?:'|’)?s a thinking process:|"
    r"thinking process:|"
    r"analy[sz]e user input:|"
    r"denkprozess:|"
    r"gedankenprozess:|"
    r"the user\b|"
    r"user said:|"
    r"the prompt\b|"
    r"the system instructions\b|"
    r"i need to\b|"
    r"we need to\b|"
    r"apply maat principles:"
    r")",
    re.IGNORECASE,
)

FREE_THINKING_PREFIXES = (
    "here's a thinking process:",
    "heres a thinking process:",
    "thinking process:",
    "analyze user input:",
    "analyse user input:",
    "denkprozess:",
    "gedankenprozess:",
    "the user",
    "user said:",
    "the prompt",
    "the system instructions",
    "i need to",
    "we need to",
    "apply maat principles:",
)

FINAL_ANSWER_LABEL_RE = re.compile(
    r"(?im)^\s*(?:"
    r"\[(?:antwort|final|final answer|output)\]|"
    r"(?:final output generation|final output|final answer|antwort|output)\s*:"
    r")\s*"
)

FINAL_ANSWER_START_RE = re.compile(
    r"(?im)^\s*(?P<answer>"
    r"gern geschehen[!,.]?|"
    r"gern[!,.]?|"
    r"gerne[!,.]?|"
    r"sehr gern[!,.]?|"
    r"kein problem[!,.]?|"
    r"hallo\b|"
    r"hi\b|"
    r"hey\b|"
    r"klar[!,.]?|"
    r"alles klar[!,.]?|"
    r"natürlich[!,.]?|"
    r"ja[!,.]?|"
    r"nein[!,.]?|"
    r"gut[!,.]?|"
    r"passt[!,.]?|"
    r"fertig[!,.]?|"
    r"hier\b|"
    r"hier\s+(?:ist|kommt|die|der|das)\b|"
    r"das\s+(?:ist|passt|geht|klingt)\b|"
    r"ich\s+(?:habe|würde|sehe|denke)\b|"
    r"die wohl bekannteste\b|"
    r"die bekannteste\b|"
    r"die formel\b|"
    r"einstein\b"
    r")",
)
INTERNAL_THINKING_HINT_RE = re.compile(
    r"(?:"
    r"self[- ]correction|"
    r"refinement during|"
    r"output generation|"
    r"proceeds?\.?|"
    r"all constraints met|"
    r"no internal tags visible|"
    r"draft(?:ing)?|"
    r"plan:|"
    r"response plan|"
    r"i'?ll\s+(?:keep|use|answer|write|provide|create)|"
    r"the prompt says|"
    r"matches the final response|"
    r"ready\.?\s*$"
    r")",
    re.IGNORECASE | re.MULTILINE,
)

MAAT_SCORE_LINE_RE = re.compile(
    r"^\s*H\s*=\s*\d+(?:\.\d+)?\s+"
    r"B\s*=\s*\d+(?:\.\d+)?\s+"
    r"S\s*=\s*\d+(?:\.\d+)?\s+"
    r"V\s*=\s*\d+(?:\.\d+)?\s+"
    r"R\s*=\s*\d+(?:\.\d+)?\s+.*?\bStability\s*=\s*\d+(?:\.\d+)?",
    re.IGNORECASE | re.MULTILINE,
)


def _is_maat_score_block(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    return bool(MAAT_SCORE_LINE_RE.search(value) and re.search(r"\bMaat Value\s*=|\bFokusfelder\s*:", value, re.IGNORECASE))


def collapse_leading_maat_score_blocks(text: str) -> str:
    value = str(text or "")
    pos = 0
    blocks: list[str] = []
    while True:
        opening = re.match(r"\s*```(?:text)?[ \t]*\n", value[pos:], flags=re.IGNORECASE)
        if not opening:
            break
        block_start = pos + opening.start()
        body_start = pos + opening.end()
        closing = re.search(r"(?m)^```[ \t]*$", value[body_start:])
        if not closing:
            break
        body_end = body_start + closing.start()
        block_end = body_start + closing.end()
        body = value[body_start:body_end]
        if not _is_maat_score_block(body):
            break
        blocks.append(value[block_start:block_end].strip())
        pos = block_end

    if len(blocks) <= 1:
        return value

    rest = value[pos:].lstrip()
    return f"{blocks[0]}\n\n{rest}".strip()


def _strip_free_thinking_preamble(text: str) -> str:
    value = str(text or "")
    output_match = FINAL_ANSWER_LABEL_RE.search(value)
    if output_match and output_match.end() < len(value):
        if FREE_THINKING_START_RE.match(value) or INTERNAL_THINKING_HINT_RE.search(value[: output_match.start()]):
            return value[output_match.end() :].strip(" \n\"'")

    answer_start = -1
    for match in FINAL_ANSWER_START_RE.finditer(text):
        if match.start("answer") < 24:
            continue
        answer_start = match.start("answer")
        break

    if answer_start >= 0:
        prefix = value[:answer_start]
        if FREE_THINKING_START_RE.match(value) or INTERNAL_THINKING_HINT_RE.search(prefix):
            return value[answer_start:].strip()

    if not FREE_THINKING_START_RE.match(value):
        return value

    return ""


def _looks_like_partial_free_thinking_start(text: str) -> bool:
    compact = re.sub(r"\s+", " ", str(text or "").strip().lower().replace("’", "'"))
    if not compact:
        return True
    if len(compact) < 4:
        return False
    return any(prefix.startswith(compact) for prefix in FREE_THINKING_PREFIXES)


def estimate_prompt_tokens(messages: list[dict[str, str]]) -> int:
    total = 0
    for message in messages:
        total += 4
        total += max(1, len(str(message.get("role", ""))) // 4)
        total += max(1, len(str(message.get("content", ""))) // 4)
    return total + 8


def _format_bytes(size: int) -> str:
    value = float(max(0, int(size)))
    units = ["B", "KB", "MB", "GB", "TB"]
    unit = 0
    while value >= 1024 and unit < len(units) - 1:
        value /= 1024
        unit += 1
    return f"{value:.1f} {units[unit]}" if unit else f"{int(value)} {units[unit]}"


def _model_detail_lines(options: dict[str, Any], adapter_name: str) -> list[str]:
    lines = [
        f"adapter={adapter_name}",
        f"model={options.get('model_name') or 'local-model'}",
        f"thinking={'on' if options.get('enable_thinking') else 'off'} maat_thinking={options.get('maat_thinking_level', 0)}%",
        f"max_tokens={options.get('max_tokens')} temp={float(options.get('temperature', 0.7)):.2f} top_p={float(options.get('top_p', 0.9)):.2f}",
    ]
    if options.get("max_tokens_reason"):
        lines.append(f"max_tokens_reason={options.get('max_tokens_reason')}")
    model_path = str(options.get("llama_model_path") or "").strip()
    if model_path:
        path = Path(model_path).expanduser()
        try:
            size = _format_bytes(path.stat().st_size)
        except OSError:
            size = "unbekannt"
        lines.extend(
            [
                f"gguf={path.name}",
                f"path={path}",
                f"size={size}",
                f"loader={options.get('loader_tuning_mode') or 'manual'} ctx={options.get('llama_n_ctx')} threads={options.get('llama_n_threads')} gpu_layers={options.get('llama_n_gpu_layers')}",
            ]
        )
        if options.get("llama_n_ctx_requested") and options.get("llama_n_ctx_requested") != options.get("llama_n_ctx"):
            lines.append(
                f"ctx_requested={options.get('llama_n_ctx_requested')} ctx_reason={options.get('llama_n_ctx_reason') or '-'}"
            )
        if options.get("llama_model_family"):
            lines.append(
                f"model_family={options.get('llama_model_family')} flash_attn={'on' if options.get('llama_flash_attn') else 'off'}"
            )
    return lines


def _prompt_detail_lines(
    messages: list[dict[str, str]],
    options: dict[str, Any],
    memory_info: dict[str, Any] | None = None,
    wiki_info: dict[str, Any] | None = None,
    project_info: dict[str, Any] | None = None,
    claim_info: dict[str, Any] | None = None,
    lessons_info: dict[str, Any] | None = None,
    compressor_info: dict[str, Any] | None = None,
) -> list[str]:
    prompt_tokens = estimate_prompt_tokens(messages)
    prompt_chars = sum(len(str(message.get("content") or "")) for message in messages)
    ctx = max(1, int(options.get("llama_n_ctx") or 4096))
    max_tokens = max(1, int(options.get("max_tokens") or 1))
    reserve = max(0, ctx - prompt_tokens - max_tokens)
    usage = min(999.0, (prompt_tokens / ctx) * 100)
    lines = [
        f"prompt≈{prompt_tokens} tokens ({usage:.1f}% von ctx {ctx})",
        f"chars={prompt_chars} messages={len(messages)} history_turns={max(0, len(messages) - 2)}",
        f"max_new_tokens={max_tokens} reserve≈{reserve}",
    ]
    if memory_info is not None:
        lines.append(
            f"memory={len(memory_info.get('memories') or [])} user={memory_info.get('current_user') or '-'}"
        )
    if wiki_info is not None:
        lines.append(
            f"offline_wiki_terms={len(wiki_info.get('terms') or [])} hits={len(wiki_info.get('hits') or [])}"
        )
    if project_info is not None:
        lines.append(
            f"project_memory={len(project_info.get('hits') or [])} block_chars={project_info.get('block_chars', 0)}"
        )
    if claim_info is not None:
        lines.append(
            f"claim_guard={claim_info.get('stance') or 'normal'} risk={claim_info.get('risk_level') or 'low'}"
        )
    if lessons_info is not None:
        lines.append(
            f"adaptive_lessons={len(lessons_info.get('lessons') or [])} hints={len(lessons_info.get('hints') or [])} "
            f"category={lessons_info.get('category') or '-'} tone={lessons_info.get('tone') or '-'}"
        )
    if compressor_info is not None:
        state = "active" if compressor_info.get("active") else "on" if compressor_info.get("enabled") else "off"
        lines.append(
            f"chat_compressor={state} trigger={compressor_info.get('trigger') or '-'} "
            f"old={compressor_info.get('old_messages', 0)} kept={compressor_info.get('kept_messages', 0)} "
            f"summary≈{compressor_info.get('summary_tokens', 0)} tokens"
        )
    if options.get("prompt_fit_reason"):
        lines.append(
            f"prompt_fit={options.get('prompt_fit_reason')} trimmed={options.get('prompt_fit_trimmed', 0)} "
            f"tokens={options.get('prompt_fit_tokens_after', '-')} / budget={options.get('prompt_fit_budget', '-')}"
        )
    return lines


def _fit_messages_to_context(
    messages: list[dict[str, str]],
    ctx: int,
    reserve_tokens: int = 768,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    before = estimate_prompt_tokens(messages)
    budget = max(512, int(ctx) - max(128, int(reserve_tokens)))
    if before <= budget:
        return messages, {
            "trimmed": 0,
            "tokens_before": before,
            "tokens_after": before,
            "budget": budget,
            "reason": "fits",
        }

    fitted = list(messages)
    trimmed = 0
    # Preserve first system block and the current user message. Drop oldest
    # prompt-history turns first; this is safer than silently overfilling llama.
    while len(fitted) > 2 and estimate_prompt_tokens(fitted) > budget:
        del fitted[1]
        trimmed += 1

    after = estimate_prompt_tokens(fitted)
    reason = "trimmed-history" if after <= budget else "system-or-current-message-too-large"
    return fitted, {
        "trimmed": trimmed,
        "tokens_before": before,
        "tokens_after": after,
        "budget": budget,
        "reason": reason,
    }


def strip_thinking_content(text: str) -> str:
    stripped = str(text or "")
    if _looks_like_partial_free_thinking_start(stripped):
        return ""
    lower = stripped.lower()
    if "<|channel>thought" in lower:
        thought_start = lower.find("<|channel>thought")
        thought_end = lower.find("<channel|>", thought_start)
        if thought_end >= 0:
            stripped = (stripped[:thought_start] + stripped[thought_end + len("<channel|>") :]).lstrip()
            lower = stripped.lower()
        else:
            stripped = stripped[:thought_start].rstrip()
            lower = stripped.lower()
    first_close = lower.find("</think>")
    first_open = lower.find("<think>")
    if first_close >= 0 and (first_open < 0 or first_close < first_open):
        stripped = stripped[first_close + len("</think>") :].lstrip()

    stripped = re.sub(
        r"\s*(here(?:'|’)?s a thinking process:|thinking process:|analy[sz]e user input:|denkprozess:|gedankenprozess:).*?</think>\s*",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stripped = re.sub(r"<think>.*?</think>\s*", "", stripped, flags=re.DOTALL | re.IGNORECASE)
    stripped = re.sub(r"<think>.*", "", stripped, flags=re.DOTALL | re.IGNORECASE)
    stripped = re.sub(r"<\|channel>thought[\s\S]*?<channel\|>\s*", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"<\|channel>thought[\s\S]*", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"<\|/?(?:turn|channel|think|bos|eos)[^>]*\|?>", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"<(?:turn|channel)\|>", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"</?(?:bos|eos)>", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(
        r"\[MAAT_REFLECTION_RULE\].*?\[/MAAT_REFLECTION_RULE\]\s*",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stripped = re.sub(
        r"\[MAAT_ANTI_HALLU\].*?\[/MAAT_ANTI_HALLU\]\s*",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stripped = re.sub(
        r"\[MAAT_ACTIVE_LESSONS\].*?\[/MAAT_ACTIVE_LESSONS\]\s*",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stripped = re.sub(
        r"\[MAAT_CONTEXT_SOURCE_STATUS\].*?\[/MAAT_CONTEXT_SOURCE_STATUS\]\s*",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stripped = re.sub(
        r"\[MAAT_CONTEXT_OPTIMIZER\].*?\[/MAAT_CONTEXT_OPTIMIZER\]\s*",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stripped = re.sub(
        r"\[MAAT_OFFLINE_WIKI\].*?\[/MAAT_OFFLINE_WIKI\]\s*",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stripped = strip_reality_tags(stripped)
    stripped = strip_core_tags(stripped)
    stripped = strip_balance_tags(stripped)
    stripped = strip_identity_tags(stripped)
    stripped = strip_claim_guard_tags(stripped)
    stripped = strip_file_builder_tags(stripped)
    stripped = re.sub(
        r"\[(denken|thinking|gedanken)\].*?\[/\1\]\s*",
        "",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    stripped = _strip_free_thinking_preamble(stripped)
    stripped = re.sub(r"@@MAAT_?RENDER_?TOKEN_?\d+@@", "", stripped, flags=re.IGNORECASE)
    return stripped.strip()


def has_thinking_content(text: str) -> bool:
    value = str(text or "")
    return bool(
        re.search(r"</?think\b|<\|channel>thought|\[(?:/?)(?:denken|thinking|gedanken)\]", value, flags=re.IGNORECASE)
        or FREE_THINKING_START_RE.match(value)
        or _looks_like_partial_free_thinking_start(value)
    )


class ChatLoop:
    def __init__(
        self,
        database: Database,
        plugins: PluginManager,
        commands: CommandRouter,
        settings: RuntimeSettings,
    ):
        self.database = database
        self.plugins = plugins
        self.commands = commands
        self.settings = settings

    def _adapter(self):
        if self.settings.model_adapter == "echo":
            return EchoAdapter()
        if self.settings.model_adapter == "llama_cpp_direct":
            return LlamaCppDirectAdapter()
        return OpenAICompatAdapter(self.settings.api_base, self.settings.model_name)

    def _context(self, chat_id: int) -> dict[str, Any]:
        return {
            "chat_id": chat_id,
            "settings": asdict(self.settings),
            "maat": {},
            "events": [],
        }

    def _spirit_settings(self) -> SpiritSettings:
        return SpiritSettings(
            enabled=bool(self.settings.spirit_enabled),
            mode=self.settings.spirit_mode,
            language=self.settings.spirit_language,
            once=bool(self.settings.spirit_once),
            use_emojis=bool(self.settings.spirit_use_emojis),
        )

    def _system_prompt(
        self,
        user_text: str = "",
        chat_id: int | None = None,
        minimal_spirit: bool = False,
        memory_prompt: str = "",
        wiki_prompt: str = "",
        project_prompt: str = "",
        file_builder_prompt: str = "",
        claim_prompt: str = "",
        lessons_prompt: str = "",
        context_optimizer_prompt: str = "",
    ) -> str:
        prompt = self.settings.system_prompt.strip()
        if self.settings.enable_thinking:
            thinking_rule = (
                "\n\n[MAAT_THINKING_MODE]\n"
                "Thinking: AN. "
                "Wenn dein Modell native Thinking/Reasoning unterstützt, nutze dessen Denkbereich. "
                "Wenn kein nativer Denkbereich verfügbar ist, schreibe eine Denkphase am Anfang "
                "ausschließlich in einem <think>...</think>-Block. "
                "Nach </think> folgt nur die finale Antwort. "
                "Keine MAAT_INTERNAL-Tags, keine Systemprompt-Zitate und keine Debug-Blöcke ausgeben. "
                "Bei kurzen Begrüßungen oder Smalltalk darf die Denkphase sehr kurz sein.\n"
                "[/MAAT_THINKING_MODE]"
            )
        else:
            thinking_rule = (
                "\n\n[MAAT_THINKING_MODE]\n"
                "Thinking: AUS. "
                "Keine sichtbaren Denkschritte, keine <think>-Blöcke, "
                "keine Analyse-Einleitung. Antworte direkt mit der finalen Antwort.\n"
                "[/MAAT_THINKING_MODE]"
            )
        core = build_core_prompt(self.settings)
        spirit = build_spirit_prompt_block(self._spirit_settings(), user_text, minimal=minimal_spirit)
        style, style_info = build_style_prompt(
            self.settings,
            user_text,
            visible_reasoning=bool(self.settings.enable_thinking),
        )
        balance, _ = build_balance_prompt(
            self.settings,
            user_text,
            style_info=style_info,
            last_eval=get_last_eval(),
            chat_id=chat_id,
        )
        emotion, _ = build_emotion_prompt(
            self.settings,
            user_text,
            last_eval=get_last_eval(),
            visible_reasoning=bool(self.settings.enable_thinking),
        )
        identity = build_identity_prompt(self.settings, user_text, chat_id)
        reality = build_reality_prompt(self.settings, user_text)
        reflection = build_reflection_prompt(self.settings, user_text)
        antihallu = build_antihallu_prompt(self.settings, user_text)
        maat_thinking = build_prompt_block(
            self.settings.maat_thinking_level,
            visible_reasoning=bool(self.settings.enable_thinking),
        )
        return f"{prompt}{thinking_rule}{context_optimizer_prompt}{core}{reality}{identity}{style}{balance}{emotion}{claim_prompt}{lessons_prompt}{project_prompt}{file_builder_prompt}{reflection}{antihallu}{wiki_prompt}{memory_prompt}{spirit}{maat_thinking}"

    def _thinking_controlled_user_text(self, user_text: str) -> str:
        text = re.sub(r"(?im)^\s*/(?:no_)?think\s*$", "", user_text.rstrip()).strip()
        text = re.sub(r"(?i)\s*/(?:no_)?think\b", "", text).strip()
        if self.settings.model_adapter == "llama_cpp_direct":
            model_name = Path(str(self.settings.llama_model_path or self.settings.model_name or "")).name.lower()
            if "qwen" in model_name:
                directive = "/think" if self.settings.enable_thinking else "/no_think"
                return f"{text}\n\n{directive}".strip()
        return text

    def _messages(
        self,
        chat_id: int,
        user_text: str,
        minimal_spirit: bool = False,
        memory_prompt: str = "",
        wiki_prompt: str = "",
        project_prompt: str = "",
        file_builder_prompt: str = "",
        claim_prompt: str = "",
        lessons_prompt: str = "",
        context_optimizer_prompt: str = "",
        context: dict[str, Any] | None = None,
        prompt_context_limit_tokens: int | None = None,
    ) -> list[dict[str, str]]:
        compressor_enabled = bool(getattr(self.settings, "chat_compressor_enabled", True))
        if compressor_enabled:
            history = self.database.chat_messages(chat_id)
            current_user_text = self._thinking_controlled_user_text(user_text)
            if history and history[-1].get("role") == "user":
                last_content = strip_file_builder_tags(strip_file_builder_chat_cards(str(history[-1].get("content") or ""))).strip()
                if last_content == user_text.strip() or last_content == current_user_text:
                    history = history[:-1]
        else:
            history = self.database.recent_messages(chat_id, limit=int(self.settings.history_limit))
        history_messages, compressor_info = compress_history_for_prompt(
            history,
            self.settings,
            context_limit_tokens=prompt_context_limit_tokens,
        )
        if context is not None:
            context["maat_chat_compressor"] = compressor_info
        system_addons = [
            str(message.get("content") or "").strip()
            for message in history_messages
            if message.get("role") == "system" and str(message.get("content") or "").strip()
        ]
        non_system_history = [message for message in history_messages if message.get("role") != "system"]
        system_prompt = self._system_prompt(
            user_text,
            chat_id,
            minimal_spirit,
            memory_prompt,
            wiki_prompt,
            project_prompt,
            file_builder_prompt,
            claim_prompt,
            lessons_prompt,
            context_optimizer_prompt,
        )
        if system_addons:
            system_prompt = f"{system_prompt}\n\n" + "\n\n".join(system_addons)
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]
        messages.extend(non_system_history)
        messages.append({"role": "user", "content": self._thinking_controlled_user_text(user_text)})
        return messages

    def _update_chat_digest(self, chat_id: int) -> dict[str, Any]:
        enabled = bool(getattr(self.settings, "chat_compressor_enabled", True))
        persist = bool(getattr(self.settings, "chat_compressor_persist_summary", True))
        auto_title = bool(getattr(self.settings, "chat_compressor_auto_title", True))
        if not enabled or (not persist and not auto_title):
            return {"enabled": enabled, "stored": False, "reason": "disabled"}

        messages = self.database.chat_messages(chat_id)
        digest = build_chat_digest(
            messages,
            max_summary_chars=int(getattr(self.settings, "chat_compressor_max_summary_chars", 3500)),
        )
        if not digest.get("title") and not digest.get("summary_short"):
            return {"enabled": enabled, "stored": False, "reason": "empty"}

        chat = self.database.update_chat_summary(
            chat_id,
            digest.get("summary_short", "") if persist else "",
            digest.get("summary_long", "") if persist else "",
            digest.get("title", "") if auto_title else "",
        )
        return {
            "enabled": enabled,
            "stored": True,
            "title": digest.get("title", ""),
            "summary_short": digest.get("summary_short", ""),
            "summary_chars": len(digest.get("summary_long", "")),
            "message_count": digest.get("message_count", 0),
            "chat": chat,
        }

    def _effective_max_tokens(self, messages: list[dict[str, str]], ctx_override: int | None = None) -> tuple[int, str]:
        configured = max(1, int(self.settings.max_tokens))
        ctx = max(256, int(ctx_override or self.settings.llama_n_ctx))
        prompt_tokens = estimate_prompt_tokens(messages)
        reserve = 96
        free = max(1, ctx - prompt_tokens - reserve)
        local_cap = 16384 if self.settings.model_adapter == "llama_cpp_direct" else 8192
        if not self.settings.max_tokens_from_ctx:
            effective = min(configured, free, local_cap)
            return effective, f"manual=min(configured:{configured}, free_ctx:{free}, safety_cap:{local_cap})"

        auto_value = free
        effective = min(auto_value, local_cap)
        return effective, f"auto_from_ctx=min(free_ctx:{auto_value}, safety_cap:{local_cap})"

    async def stream(self, user_text: str, chat_id: int | None = None) -> AsyncIterator[str]:
        chat_id = self.database.get_or_create_chat(chat_id)
        context = self._context(chat_id)
        raw_text = (user_text or "").strip()
        if not raw_text:
            yield sse("done", {"chat_id": chat_id, "empty": True})
            return

        yield sse("meta", {"chat_id": chat_id, "plugins": self.plugins.info()})
        had_prior_messages = bool(self.database.recent_messages(chat_id, limit=1))

        if self.commands.match(raw_text):
            reply = self.commands.execute(raw_text, context)
            self.database.add_message(chat_id, "user", raw_text)
            self.database.add_message(chat_id, "assistant", reply)
            yield sse("replace", {"content": reply})
            yield sse("done", {"chat_id": chat_id})
            return

        handled, processed_text = self.plugins.before_chat(raw_text, context)
        self.database.add_message(chat_id, "user", raw_text)

        if handled:
            reply = processed_text
            self.database.add_message(chat_id, "assistant", reply)
            yield sse("replace", {"content": reply})
            yield sse("done", {"chat_id": chat_id})
            return

        chat_search_answer = direct_chat_search_answer(self.database, self.settings, processed_text)
        if chat_search_answer is not None:
            self.database.add_message(chat_id, "assistant", chat_search_answer)
            yield sse("replace", {"content": chat_search_answer})
            yield sse("done", {"chat_id": chat_id})
            return

        reality_answer = direct_reality_answer(self.settings, processed_text)
        if reality_answer is not None:
            self.database.add_message(chat_id, "assistant", reality_answer)
            yield sse("replace", {"content": reality_answer})
            yield sse(
                "maat_reality",
                {
                    "direct": True,
                    "question": processed_text,
                    "answer": reality_answer,
                },
            )
            yield sse("done", {"chat_id": chat_id})
            return

        full = ""
        visible_streamed = ""
        minimal_spirit = bool(had_prior_messages) and bool(self.settings.spirit_once)
        _, style_info = build_style_prompt(
            self.settings,
            processed_text,
            visible_reasoning=bool(self.settings.enable_thinking),
        )
        context["maat_style"] = style_info
        if style_info.get("debug"):
            print(
                "[MAAT Web Core][style] "
                f"intent={style_info.get('intent')} tone={style_info.get('tone_mode')} "
                f"vector={style_info.get('tone_vector')} opening={style_info.get('opening_mode')}",
                flush=True,
            )
        balance_info = balance_state(self.settings, processed_text, style_info=style_info, last_eval=get_last_eval())
        context["maat_balance"] = balance_info
        if balance_info.get("debug"):
            print(
                "[MAAT Web Core][balance] "
                f"enabled={balance_info.get('enabled')} level={balance_info.get('level')} "
                f"skip={balance_info.get('skip')} pressure={balance_info.get('agreement_pressure')} "
                f"context={balance_info.get('context_type')} last_hint={balance_info.get('last_hint')}",
                flush=True,
            )
            yield sse(
                "log",
                {
                    "source": "balance",
                    "title": "MAAT Balance",
                    "lines": [
                        f"enabled={balance_info.get('enabled')} level={balance_info.get('level')}",
                        f"skip={balance_info.get('skip')} pressure={balance_info.get('agreement_pressure')}",
                        f"context={balance_info.get('context_type')} last_hint={balance_info.get('last_hint') or '-'} cci={balance_info.get('last_cci_state') or '-'}",
                    ],
                },
            )
        _, emotion_info = build_emotion_prompt(
            self.settings,
            processed_text,
            last_eval=get_last_eval(),
            visible_reasoning=bool(self.settings.enable_thinking),
        )
        context["maat_emotion"] = emotion_info
        if emotion_info.get("debug") and emotion_info.get("result"):
            result = emotion_info["result"]
            print(
                "[MAAT Web Core][emotion] "
                f"emotion={result.get('emotion')} e={result.get('e_val')} "
                f"formula={result.get('formula_val')} mode={emotion_info.get('mode')} lang={emotion_info.get('language')}",
                flush=True,
            )
        wiki_prompt, wiki_info = build_wiki_prompt(self.settings, processed_text)
        context["offline_wiki"] = wiki_info
        if getattr(self.settings, "offline_wiki_debug", False) and (
            wiki_info.get("terms") or wiki_info.get("hits") or wiki_info.get("errors")
        ):
            hits = wiki_info.get("hits") or []
            errors = wiki_info.get("errors") or []
            print(
                "[MAAT Web Core][offline_wiki] "
                f"terms={wiki_info.get('terms') or []} hits={len(hits)} errors={errors}",
                flush=True,
            )
            yield sse(
                "log",
                {
                    "source": "offline_wiki",
                    "title": f"Offline Wiki · {len(hits)} Treffer",
                    "lines": [
                        f"terms={', '.join(wiki_info.get('terms') or []) or '-'}",
                        *[
                            f"{index + 1}. {hit.get('title')} · {hit.get('source')}"
                            for index, hit in enumerate(hits[:5])
                        ],
                        *[f"MISS: {error}" for error in errors[:3]],
                    ],
                },
            )
        memory_prompt, memory_info = build_memory_prompt(self.database, self.settings, processed_text)
        context["super_memory"] = memory_info
        if getattr(self.settings, "supermem_debug", False):
            memory_debug_items = []
            print(
                "[MAAT Web Core][supermem] "
                f"user={memory_info.get('current_user')} memories={len(memory_info.get('memories') or [])}",
                flush=True,
            )
            for index, item in enumerate((memory_info.get("memories") or [])[:5], 1):
                memory_debug_items.append(
                    {
                        "index": index,
                        "source": item.get("source") or item.get("layer") or "memory",
                        "score": float(item.get("score") or 0),
                        "category": item.get("category") or "",
                        "memory_type": item.get("memory_type") or "",
                        "maat_field": item.get("maat_field") or "",
                        "author_user": item.get("author_user") or "",
                        "content": str(item.get("content") or "")[:240],
                    }
                )
                print(
                    "[MAAT Web Core][supermem] "
                    f"{index}. {item.get('source')} score={float(item.get('score') or 0):.2f} "
                    f"{str(item.get('content') or '')[:90]}",
                    flush=True,
                )
            yield sse(
                "log",
                {
                    "source": "supermem",
                    "title": f"SuperMemory Recall · User {memory_info.get('current_user')} · {len(memory_info.get('memories') or [])} Treffer",
                    "items": memory_debug_items,
                },
            )
        claim_prompt, claim_info = build_claim_prompt(self.settings, processed_text)
        context["maat_claim_guard"] = claim_info
        if claim_info.get("needs_challenge"):
            print(
                "[MAAT Web Core][claim_guard] "
                f"stance={claim_info.get('stance')} risk={claim_info.get('risk_level')} "
                f"score={claim_info.get('risk_score')} reasons={claim_info.get('reasons')}",
                flush=True,
            )
            yield sse(
                "log",
                {
                    "source": "claim",
                    "title": "MAAT Claim Guard",
                    "lines": claim_report_lines(claim_info),
                },
            )
        lessons_prompt, lessons_info = build_active_lessons_block(self.database, self.settings, processed_text, context)
        context["maat_adaptive_learning"] = lessons_info
        if getattr(self.settings, "adaptive_learning_debug", False):
            lesson_lines = [
                f"category={lessons_info.get('category') or '-'} tone={lessons_info.get('tone') or '-'}",
                f"lessons={len(lessons_info.get('lessons') or [])} hints={len(lessons_info.get('hints') or [])}",
            ]
            for item in (lessons_info.get("lessons") or [])[:2]:
                lesson_lines.append(
                    f"- {item.get('category')}/{item.get('lesson_type')}: {str(item.get('lesson') or '')[:160]}"
                )
            for hint in (lessons_info.get("hints") or [])[:3]:
                lesson_lines.append(f"- Hint: {hint}")
            yield sse(
                "log",
                {
                    "source": "adaptive_learning",
                    "title": "MAAT Adaptive Learning",
                    "lines": lesson_lines,
                },
            )
        project_prompt, project_info = build_project_prompt(self.database, self.settings, processed_text)
        context["maat_project_memory"] = project_info
        if getattr(self.settings, "project_memory_debug", False) and project_info.get("hits"):
            yield sse(
                "log",
                {
                    "source": "project_memory",
                    "title": f"Project Memory · {len(project_info.get('hits') or [])} Treffer",
                    "lines": [
                        f"block_chars={project_info.get('block_chars', 0)} top_k={getattr(self.settings, 'project_memory_top_k', 2)}",
                        *[
                            f"- {item.get('name')} score={item.get('score')} tags={', '.join(item.get('tags') or [])}"
                            for item in (project_info.get("hits") or [])[:5]
                        ],
                    ],
                },
            )
        file_builder_prompt, file_builder_info = build_file_builder_prompt(self.settings, processed_text)
        feedback_prompt, file_builder_feedback = build_file_builder_feedback_prompt(self.settings)
        if feedback_prompt:
            file_builder_prompt = f"{feedback_prompt}{file_builder_prompt}"
            file_builder_info["feedback"] = file_builder_feedback
        context["maat_file_builder"] = file_builder_info
        if getattr(self.settings, "file_builder_debug", False) and (
            file_builder_info.get("wants_file") or file_builder_info.get("feedback", {}).get("pending")
        ):
            yield sse(
                "log",
                {
                    "source": "docs",
                    "title": "MAAT Docs/File Builder",
                    "lines": [
                        f"wants_file={file_builder_info.get('wants_file')}",
                        f"requested={file_builder_info.get('requested_name') or '-'}",
                        f"ext={file_builder_info.get('requested_ext') or '-'}",
                        f"feedback={file_builder_info.get('feedback', {}).get('filename') or '-'}",
                    ],
                },
            )
        context_optimizer_prompt, memory_prompt, context_optimizer_info = optimize_context(
            self.settings,
            user_text=processed_text,
            memory_prompt=memory_prompt,
            wiki_prompt=wiki_prompt,
            project_prompt=project_prompt,
            lessons_prompt=lessons_prompt,
            file_builder_prompt=file_builder_prompt,
        )
        context["maat_context_optimizer"] = context_optimizer_info
        if getattr(self.settings, "context_optimizer_debug", False):
            yield sse(
                "log",
                {
                    "source": "context_optimizer",
                    "title": "MAAT Context Optimizer",
                    "lines": context_optimizer_report_lines(context_optimizer_info),
                },
            )
        loader_values = effective_loader_values(self.settings)
        options = {
            "model_name": self.settings.model_name,
            "llama_model_path": self.settings.llama_model_path,
            "llama_n_ctx": loader_values["llama_n_ctx"],
            "llama_n_threads": loader_values["llama_n_threads"],
            "llama_n_gpu_layers": loader_values["llama_n_gpu_layers"],
            "loader_tuning_mode": loader_values["loader_tuning_mode"],
            "enable_thinking": self.settings.enable_thinking,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "max_tokens_from_ctx": self.settings.max_tokens_from_ctx,
            "maat_thinking_level": self.settings.maat_thinking_level,
        }
        if self.settings.model_adapter == "llama_cpp_direct":
            options = normalize_options_for_model(options)
        messages = self._messages(
            chat_id,
            processed_text,
            minimal_spirit=minimal_spirit,
            memory_prompt=memory_prompt,
            wiki_prompt=wiki_prompt,
            project_prompt=project_prompt,
            file_builder_prompt=file_builder_prompt,
            claim_prompt=claim_prompt,
            lessons_prompt=lessons_prompt,
            context_optimizer_prompt=context_optimizer_prompt,
            context=context,
            prompt_context_limit_tokens=int(options.get("llama_n_ctx") or self.settings.llama_n_ctx),
        )
        messages, prompt_fit_info = _fit_messages_to_context(messages, int(options.get("llama_n_ctx") or 4096))
        options.update(
            {
                "prompt_fit_reason": prompt_fit_info.get("reason"),
                "prompt_fit_trimmed": prompt_fit_info.get("trimmed"),
                "prompt_fit_tokens_after": prompt_fit_info.get("tokens_after"),
                "prompt_fit_budget": prompt_fit_info.get("budget"),
            }
        )
        compressor_info = context.get("maat_chat_compressor") or {}
        if compressor_info.get("active") or getattr(self.settings, "chat_compressor_debug", False):
            yield sse(
                "log",
                {
                    "source": "compressor",
                    "title": "MAAT Chat Compressor",
                    "lines": compressor_report_lines(compressor_info),
                },
            )
        options["max_tokens"], options["max_tokens_reason"] = self._effective_max_tokens(messages, int(options["llama_n_ctx"]))
        adapter_name = self.settings.model_adapter
        prompt_tokens = estimate_prompt_tokens(messages)
        prompt_started = time.perf_counter()
        yield sse(
            "log",
            {
                "source": "model",
                "title": "Modell-/Adapterdetails",
                "lines": _model_detail_lines(options, adapter_name),
            },
        )
        yield sse(
            "log",
            {
                "source": "prompt",
                "title": "Prompt vorbereitet",
                "lines": _prompt_detail_lines(
                    messages,
                    options,
                    memory_info,
                    wiki_info,
                    project_info,
                    claim_info,
                    lessons_info,
                    compressor_info,
                ),
            },
        )

        async def produce_adapter_events(queue: asyncio.Queue[tuple[str, Any]]) -> None:
            try:
                async for item in self._adapter().stream_chat(messages, options):
                    await queue.put(("item", item))
            except Exception as exc:
                await queue.put(("error", exc))
            finally:
                await queue.put(("done", None))

        def heartbeat_lines(elapsed: float) -> list[str]:
            ctx = max(1, int(options.get("llama_n_ctx") or 4096))
            return [
                f"elapsed={elapsed:.1f}s",
                f"prompt≈{prompt_tokens} tokens von ctx {ctx}",
                "warte auf erstes Token; Backend evaluiert vermutlich Prompt/KV-Cache/Modell",
            ]

        adapter_queue: asyncio.Queue[tuple[str, Any]] | None = None
        producer_task: asyncio.Task[None] | None = None
        try:
            adapter_queue = asyncio.Queue()
            producer_task = asyncio.create_task(produce_adapter_events(adapter_queue))
            first_token_seen = False
            progress_mark = 0
            progress_marks = [2, 5, 10, 20, 30, 45, 60, 90, 120, 180, 240, 300]
            while True:
                try:
                    kind, payload = await asyncio.wait_for(adapter_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if not first_token_seen:
                        elapsed = time.perf_counter() - prompt_started
                        reached = [mark for mark in progress_marks if elapsed >= mark]
                        next_mark = reached[-1] if reached else 0
                        if next_mark and next_mark != progress_mark:
                            progress_mark = next_mark
                            yield sse(
                                "log",
                                {
                                    "source": "progress",
                                    "title": "Prompt Processing läuft",
                                    "lines": heartbeat_lines(elapsed),
                                },
                            )
                    continue

                if kind == "error":
                    raise payload
                if kind == "done":
                    break
                if kind != "item":
                    continue

                item = payload
                if isinstance(item, dict):
                    if item.get("event") == "log":
                        data = item.get("data")
                        if isinstance(data, dict):
                            yield sse("log", data)
                        continue
                    if item.get("event") == "token":
                        chunk = str(item.get("content") or "")
                    else:
                        continue
                else:
                    chunk = str(item)
                if not first_token_seen and chunk:
                    first_token_seen = True
                    elapsed = time.perf_counter() - prompt_started
                    yield sse(
                        "log",
                        {
                            "source": "progress",
                            "title": "Erstes Token sichtbar",
                            "lines": [
                                f"erstes_token_nach={elapsed:.2f}s",
                                f"prompt≈{prompt_tokens} tokens",
                            ],
                        },
                    )
                full += chunk
                if self.settings.enable_thinking:
                    yield sse("token", {"content": chunk})
                    continue

                visible = strip_thinking_content(full)
                if not visible:
                    continue
                if visible.startswith(visible_streamed):
                    delta = visible[len(visible_streamed) :]
                    if delta:
                        visible_streamed = visible
                        yield sse("token", {"content": delta})
                elif visible != visible_streamed:
                    visible_streamed = visible
                    yield sse("replace", {"content": visible})
        except Exception as exc:
            full = (
                "Ich konnte das lokale Modell gerade nicht erreichen.\n\n"
                f"Fehler: `{exc}`\n\n"
                "Prüfe Adapter, Modellpfad oder ob die konfigurierte lokale OpenAI-kompatible API läuft."
            )
            yield sse("replace", {"content": full, "error": True})
        finally:
            if producer_task and not producer_task.done():
                producer_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await producer_task

        final_text = self.plugins.before_final_response(full, context)
        final_text = self.plugins.after_response(final_text, context)
        final_text = strip_routine_opening(processed_text, final_text, self.settings)
        final_text = strip_claim_guard_tags(final_text)
        if not self.settings.enable_thinking:
            final_text = strip_thinking_content(final_text)

        claim_guarded_text, claim_after_info = apply_claim_guard_output(self.settings, processed_text, final_text)
        if claim_after_info:
            context["maat_claim_guard"] = {
                **(context.get("maat_claim_guard") or {}),
                **claim_after_info,
            }
        if claim_guarded_text != final_text:
            final_text = claim_guarded_text
            yield sse(
                "log",
                {
                    "source": "claim",
                    "title": "MAAT Claim Guard",
                    "lines": claim_report_lines(context.get("maat_claim_guard")),
                },
            )

        prelim_visible_text = strip_thinking_content(final_text)
        prelim_visible_text = prelim_visible_text or ("" if has_thinking_content(final_text) else final_text.strip())
        if self.settings.engine_enabled:
            context["maat_engine"] = evaluate_text(prelim_visible_text)

        rewritten_text, rewrite_info = apply_rewrite_loop(
            self.settings,
            processed_text,
            final_text,
            context.get("maat_engine"),
        )
        context["maat_rewrite"] = rewrite_info
        if rewrite_info.get("changed"):
            final_text = rewritten_text
            if getattr(self.settings, "rewrite_show_banner", False):
                banner = "```text\n" + "\n".join(rewrite_report_lines(rewrite_info)) + "\n```"
                final_text = f"{banner}\n\n{final_text}".strip()
            prelim_visible_text = strip_thinking_content(final_text)
            prelim_visible_text = prelim_visible_text or ("" if has_thinking_content(final_text) else final_text.strip())
            if self.settings.engine_enabled:
                context["maat_engine"] = evaluate_text(prelim_visible_text)
            if self.settings.balance_debug or getattr(self.settings, "style_debug", False):
                yield sse(
                    "log",
                    {
                        "source": "rewrite",
                        "title": "MAAT Rewrite",
                        "lines": rewrite_report_lines(rewrite_info),
                    },
                )

        guarded_text, antihallu_eval = apply_antihallu_guard(self.settings, processed_text, final_text, context)
        if antihallu_eval:
            context["maat_antihallu"] = antihallu_eval
            if guarded_text != final_text:
                final_text = guarded_text

        final_text, memory_after = process_turn_memory(self.database, self.settings, processed_text, final_text)
        context["super_memory_after"] = memory_after
        if getattr(self.settings, "supermem_debug", False):
            print(
                "[MAAT Web Core][supermem] "
                f"saves={len(memory_after.get('stored_saves') or [])} autostore={memory_after.get('autostore')}",
                flush=True,
            )
        stripped_final_text = strip_thinking_content(final_text)
        visible_final_text = stripped_final_text or ("" if has_thinking_content(final_text) else final_text.strip())

        engine_eval = None
        if self.settings.engine_enabled:
            engine_eval = evaluate_text(visible_final_text)
            context["maat_engine"] = engine_eval
            context.setdefault("maat", {}).update(
                {
                    "H": engine_eval["H"],
                    "B": engine_eval["B"],
                    "S": engine_eval["S"],
                    "V": engine_eval["V"],
                    "R": engine_eval["R"],
                    "stability": engine_eval["stability"],
                    "maat_value": engine_eval["maat_value"],
                    "cci_runtime": engine_eval["cci_runtime"],
                    "cci_state": engine_eval["cci_state"],
                }
            )
            remember_eval(engine_eval)
            if self.settings.advanced_cci_enabled:
                advanced_cci = compute_advanced_cci(
                    processed_text,
                    visible_final_text,
                    engine_eval,
                    kappa=self.settings.advanced_cci_kappa,
                )
                context["maat_cci"] = advanced_cci
                remember_advanced_cci(advanced_cci)
            feedback_output_text = visible_final_text
            if self.settings.engine_show_in_chat:
                debug_lines_out = debug_lines(
                    engine_eval,
                    include_cci=bool(self.settings.engine_show_cci_debug),
                )
                if self.settings.advanced_cci_enabled and self.settings.advanced_cci_show_debug:
                    debug_lines_out.extend(advanced_cci_report_lines(context.get("maat_cci")))
                debug = "```text\n" + "\n".join(debug_lines_out) + "\n```"
                final_text = f"{debug}\n\n{final_text}".strip()
                visible_final_text = f"{debug}\n\n{visible_final_text}".strip()
        else:
            feedback_output_text = visible_final_text

        adaptive_feedback = record_silent_feedback(
            self.database,
            self.settings,
            processed_text,
            feedback_output_text,
            engine_eval,
            context,
        )
        context["maat_adaptive_learning_after"] = adaptive_feedback
        if getattr(self.settings, "adaptive_learning_debug", False):
            stored = adaptive_feedback.get("stored") or []
            hints = adaptive_feedback.get("hints") or []
            yield sse(
                "log",
                {
                    "source": "adaptive_learning",
                    "title": "MAAT Silent Feedback",
                    "lines": [
                        f"category={adaptive_feedback.get('category') or '-'} intent={adaptive_feedback.get('intent') or '-'}",
                        f"stored={sum(1 for item in stored if item.get('stored'))} hints={len(hints)}",
                        *[f"- Hint: {hint}" for hint in hints[:3]],
                        *[
                            f"- {item.get('reason') or 'stored'}: {((item.get('item') or {}).get('lesson') or '')[:140]}"
                            for item in stored[:3]
                        ],
                    ],
                },
            )

        feedback_report = record_feedback_report(
            self.database,
            self.settings,
            processed_text,
            feedback_output_text,
            context,
        )
        context["maat_feedback_tool"] = feedback_report
        if getattr(self.settings, "feedback_debug", False) and feedback_report.get("enabled"):
            report = feedback_report.get("last") or {}
            findings = report.get("findings") or []
            yield sse(
                "log",
                {
                    "source": "feedback",
                    "title": "MAAT Feedback Tool",
                    "lines": [
                        feedback_score_line(report),
                        f"critical={'yes' if report.get('critical') else 'no'} intent={report.get('intent') or '-'} self_lessons={report.get('self_lessons', 0)}",
                        *[
                            f"- {item.get('field', '-')}/{item.get('severity', '-')}: {str(item.get('recommendation') or item.get('reason') or '')[:160]}"
                            for item in findings[:3]
                        ],
                    ],
                },
            )

        final_text, reflection_eval = apply_reflection_banner(
            self.settings,
            processed_text,
            final_text,
            engine_eval,
            engine_debug_visible=bool(self.settings.engine_show_in_chat),
        )
        if reflection_eval:
            context["maat_reflection"] = reflection_eval
            if final_text != visible_final_text:
                visible_final_text, _ = apply_reflection_banner(
                    self.settings,
                    processed_text,
                    visible_final_text,
                    engine_eval,
                    engine_debug_visible=bool(self.settings.engine_show_in_chat),
                )

        final_text = collapse_leading_maat_score_blocks(final_text)
        visible_final_text = collapse_leading_maat_score_blocks(visible_final_text)

        final_text, file_builder_after = process_file_builder_output(
            self.settings,
            processed_text,
            final_text,
            context,
        )
        if file_builder_after.get("records") or file_builder_after.get("errors"):
            context["maat_file_builder"] = {
                **(context.get("maat_file_builder") or {}),
                **file_builder_after,
            }
            visible_final_text = strip_thinking_content(final_text)
            visible_final_text = visible_final_text or ("" if has_thinking_content(final_text) else final_text.strip())
            visible_final_text = collapse_leading_maat_score_blocks(visible_final_text)
            if getattr(self.settings, "file_builder_debug", False):
                yield sse(
                    "log",
                    {
                        "source": "docs",
                        "title": "MAAT Docs/File Builder",
                        "lines": [
                            f"records={len(file_builder_after.get('records') or [])}",
                            *[
                                f"- {record.get('filename')} · {record.get('relative_path')}"
                                for record in (file_builder_after.get("records") or [])[:5]
                            ],
                            *[f"ERR: {error}" for error in (file_builder_after.get("errors") or [])[:3]],
                        ],
                    },
                )

        self.plugins.after_final_response(final_text, context)

        if final_text != full:
            yield sse("replace", {"content": final_text})

        self.database.add_message(chat_id, "assistant", visible_final_text)
        try:
            chat_digest = self._update_chat_digest(chat_id)
        except Exception as exc:
            chat_digest = {"enabled": bool(getattr(self.settings, "chat_compressor_enabled", True)), "stored": False, "error": str(exc)}
            if getattr(self.settings, "chat_compressor_debug", False):
                yield sse(
                    "log",
                    {
                        "source": "compressor",
                        "title": "MAAT Chat Digest Fehler",
                        "lines": [str(exc)],
                    },
                )
        if chat_digest.get("stored"):
            context["maat_chat_digest"] = chat_digest
            if getattr(self.settings, "chat_compressor_debug", False):
                yield sse(
                    "log",
                    {
                        "source": "compressor",
                        "title": "MAAT Chat Digest",
                        "lines": [
                            f"title={chat_digest.get('title') or '-'}",
                            f"messages={chat_digest.get('message_count', 0)} summary_chars={chat_digest.get('summary_chars', 0)}",
                            f"summary={str(chat_digest.get('summary_short') or '')[:220]}",
                        ],
                    },
                )
        if context.get("maat"):
            yield sse("maat", context["maat"])
        if context.get("maat_engine"):
            yield sse("maat_engine", context["maat_engine"])
        if context.get("maat_cci"):
            yield sse("maat_cci", context["maat_cci"])
        if context.get("maat_reflection"):
            yield sse("maat_reflection", context["maat_reflection"])
        if context.get("maat_claim_guard"):
            yield sse("maat_claim_guard", context["maat_claim_guard"])
        if context.get("maat_rewrite"):
            yield sse("maat_rewrite", context["maat_rewrite"])
        if context.get("maat_antihallu"):
            yield sse("maat_antihallu", context["maat_antihallu"])
        if context.get("maat_balance"):
            yield sse("maat_balance", context["maat_balance"])
        if context.get("maat_adaptive_learning"):
            yield sse("maat_adaptive_learning", context["maat_adaptive_learning"])
        if context.get("maat_adaptive_learning_after"):
            yield sse("maat_adaptive_learning_after", context["maat_adaptive_learning_after"])
        if context.get("maat_feedback_tool"):
            yield sse("maat_feedback_tool", context["maat_feedback_tool"])
        if context.get("maat_project_memory"):
            yield sse("maat_project_memory", context["maat_project_memory"])
        if context.get("maat_file_builder"):
            yield sse("maat_file_builder", context["maat_file_builder"])
        if context.get("maat_chat_compressor"):
            yield sse("maat_chat_compressor", context["maat_chat_compressor"])
        if context.get("maat_chat_digest"):
            yield sse("maat_chat_digest", context["maat_chat_digest"])
        yield sse("done", {"chat_id": chat_id})
