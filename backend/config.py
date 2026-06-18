from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


APP_NAME = "MAAT Web Core"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("MAAT_WEB_HOME", PROJECT_ROOT / "data")).expanduser().resolve()
PLUGIN_DIR = Path(os.environ.get("MAAT_WEB_PLUGINS", PROJECT_ROOT / "plugins")).expanduser().resolve()
SETTINGS_PATH = DATA_DIR / "settings.json"
DATABASE_PATH = DATA_DIR / "maat_web.sqlite"

DEFAULT_GGUF_MODEL_DIRS = [
    PROJECT_ROOT / "models",
    PROJECT_ROOT.parent / "models",
]


DEFAULT_SYSTEM_PROMPT = """\
Du bist MAAT-KI im lokalen MAAT Web Core.

Nutze die MAAT-Prinzipien still:
- H: klare Struktur und Kohärenz
- B: faire Abwägung, keine blinde Zustimmung
- S: nützliche Ideen und kreative Verbindungen
- V: Bezug zum Kontext und zum Menschen
- R: Ehrlichkeit, Unsicherheit markieren, nichts erfinden

Antworte auf Deutsch, direkt, warm und ohne interne Tags auszugeben.
"""


@dataclass
class RuntimeSettings:
    model_adapter: str = "llama_cpp_direct"
    api_base: str = "http://127.0.0.1:7860/v1"
    model_name: str = "GGUF"
    llama_model_path: str = ""
    llama_n_ctx: int = 4096
    llama_n_threads: int = 8
    llama_n_gpu_layers: int = 0
    loader_tuning_mode: str = "manual"
    loader_scan_result: dict[str, Any] = field(default_factory=dict)
    gguf_model_dirs_custom: str = "./models"
    favorite_model_paths: list[str] = field(default_factory=list)
    enable_thinking: bool = False
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 4096
    max_tokens_from_ctx: bool = False
    history_limit: int = 12
    chat_compressor_enabled: bool = True
    chat_compressor_trigger_turns: int = 10
    chat_compressor_keep_recent_turns: int = 6
    chat_compressor_context_threshold_tokens: int = 12000
    chat_compressor_max_summary_chars: int = 3500
    chat_compressor_chars_per_token: float = 4.0
    chat_compressor_auto_title: bool = True
    chat_compressor_persist_summary: bool = True
    chat_compressor_debug: bool = False
    context_optimizer_enabled: bool = True
    context_optimizer_debug: bool = False
    context_optimizer_current_user_block: bool = True
    context_optimizer_max_memory_items: int = 6
    context_optimizer_max_memory_chars: int = 2600
    chat_search_enabled: bool = True
    chat_search_auto_index: bool = True
    chat_search_include_webcore: bool = True
    chat_search_debug: bool = False
    chat_search_max_results: int = 6
    chat_search_scan_interval: int = 45
    chat_search_external_roots: str = (
        "./logs"
    )
    maat_thinking_level: int = 0
    spirit_enabled: bool = False
    spirit_mode: str = "standard"
    spirit_language: str = "auto"
    spirit_once: bool = True
    spirit_use_emojis: bool = True
    style_enabled: bool = True
    style_debug: bool = False
    style_greeting_override: bool = True
    style_emoji_mode: str = "few"
    style_old_smiley_mode: str = "none"
    style_tone_mode: str = "friendly"
    style_tone_auto: bool = True
    style_opening_mode: str = "varied"
    style_density_mode: str = "normal"
    style_heading_mode: str = "simple"
    style_list_mode: str = "auto"
    emotion_enabled: bool = True
    emotion_debug: bool = False
    emotion_mode: str = "full"
    emotion_language: str = "auto"
    offline_wiki_enabled: bool = False
    offline_wiki_auto: bool = True
    offline_wiki_zim_path: str = ""
    offline_wiki_max_chars: int = 1400
    offline_wiki_multi_max_chars: int = 700
    offline_wiki_max_terms: int = 2
    offline_wiki_min_term_len: int = 3
    offline_wiki_debug: bool = False
    offline_wiki_log: bool = True
    project_memory_enabled: bool = True
    project_memory_top_k: int = 2
    project_memory_max_chars: int = 2600
    project_memory_debug: bool = False
    file_builder_enabled: bool = True
    file_builder_inject_instructions: bool = True
    file_builder_replace_blocks: bool = True
    file_builder_show_source_code: bool = True
    file_builder_auto_capture_fences: bool = True
    file_builder_compile_tex_pdf: bool = True
    file_builder_python_syntax_check: bool = True
    file_builder_python_run_enabled: bool = False
    file_builder_python_run_in_terminal: bool = False
    file_builder_inject_feedback: bool = True
    file_builder_preview_chars: int = 5000
    file_builder_max_bytes: int = 2_000_000
    file_builder_tex_timeout: int = 45
    file_builder_python_timeout: int = 8
    file_builder_feedback_chars: int = 6000
    file_builder_debug: bool = False
    reality_enabled: bool = True
    reality_inject_time: bool = True
    reality_show_banner: bool = False
    supermem_enabled: bool = True
    supermem_autostore: bool = True
    supermem_autorecall: bool = True
    supermem_debug: bool = False
    supermem_top_k: int = 5
    supermem_min_score: float = 0.15
    supermem_max_memories: int = 1000
    supermem_allow_model_saves: bool = True
    supermem_show_save_box: bool = True
    supermem_dreaming_enabled: bool = True
    supermem_dream_on_load: bool = False
    supermem_dream_hours: int = 24
    supermem_archive_enabled: bool = True
    supermem_archive_after_days: int = 30
    supermem_person_recall: bool = True
    supermem_person_graph: bool = True
    supermem_person_top_k: int = 4
    supermem_person_graph_top_k: int = 2
    supermem_current_user: str = "User"
    supermem_known_users: str = "User"
    supermem_person_names: str = (
        "Alice, Bob, Charlie"
    )
    supermem_person_ambiguous_names: str = ""
    supermem_prefer_user_memories: bool = True
    supermem_user_memory_bonus: float = 0.12
    supermem_autostore_assistant: bool = False
    supermem_autostore_user_min: float = 0.38
    supermem_autostore_assistant_min: float = 0.62
    supermem_autostore_max_chars: int = 1200
    maat_core_enabled: bool = True
    maat_core_mode: str = "standard"
    engine_enabled: bool = True
    engine_show_in_chat: bool = False
    engine_show_cci_debug: bool = False
    advanced_cci_enabled: bool = True
    advanced_cci_show_debug: bool = False
    advanced_cci_kappa: float = 0.5
    adaptive_learning_enabled: bool = True
    adaptive_learning_inject: bool = True
    adaptive_learning_per_turn: int = 2
    adaptive_learning_exploration_rate: float = 0.25
    adaptive_learning_user_bonus: float = 0.20
    adaptive_learning_age_penalty_per_day: float = 0.006
    adaptive_learning_usage_bonus: float = 0.08
    adaptive_learning_debug: bool = False
    feedback_enabled: bool = True
    feedback_debug: bool = False
    feedback_history_limit: int = 25
    feedback_warn_below_b: float = 0.60
    feedback_warn_below_r: float = 0.75
    feedback_warn_below_h: float = 0.65
    feedback_self_learning_enabled: bool = True
    feedback_self_learning_per_report: int = 2
    claim_guard_enabled: bool = True
    claim_guard_mode: str = "balanced"
    claim_guard_after_output: bool = True
    claim_guard_show_banner: bool = False
    rewrite_enabled: bool = True
    rewrite_mode: str = "light"
    rewrite_show_banner: bool = False
    rewrite_trim_outputs: bool = False
    rewrite_field_weak: float = 6.2
    rewrite_field_strong: float = 5.0
    rewrite_r_min: float = 7.0
    balance_enabled: bool = True
    balance_level: str = "standard"
    balance_debug: bool = False
    balance_once: bool = False
    balance_self_reflect: bool = True
    balance_dynamic: bool = True
    balance_context_weights: bool = True
    balance_counterpart_mode: bool = True
    reflection_enabled: bool = True
    reflection_banner: bool = False
    reflection_mode: str = "auto"
    reflection_prompt_rule: bool = True
    antihallu_enabled: bool = True
    antihallu_mode: str = "soften"
    antihallu_show_banner: bool = False
    antihallu_soften_threshold: float = 0.55
    antihallu_strict_threshold: float = 0.85
    antihallu_gap_questions: bool = True
    antihallu_symbolic_lenient: bool = True
    identity_enabled: bool = True
    identity_name: str = "MAAT-KI"
    identity_mode: str = "balanced"
    identity_once: bool = True
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PLUGIN_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> RuntimeSettings:
    ensure_directories()
    data: dict[str, Any] = {}
    if SETTINGS_PATH.exists():
        try:
            loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}

    settings = RuntimeSettings()
    for key, value in data.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings


def save_settings(settings: RuntimeSettings) -> None:
    ensure_directories()
    SETTINGS_PATH.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def gguf_model_dirs(custom_dirs: str = "") -> list[Path]:
    dirs = list(DEFAULT_GGUF_MODEL_DIRS)
    for item in re_split_paths(custom_dirs):
        dirs.append(Path(item).expanduser())
    extra = os.environ.get("MAAT_WEB_GGUF_DIRS", "")
    for item in re_split_paths(extra):
        dirs.append(Path(item).expanduser())
    seen: set[str] = set()
    unique: list[Path] = []
    for path in dirs:
        try:
            resolved = path.expanduser().resolve()
        except Exception:
            resolved = path.expanduser()
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


def re_split_paths(value: str) -> list[str]:
    raw = str(value or "")
    parts = []
    for chunk in raw.replace(",", "\n").splitlines():
        chunk = chunk.strip()
        if not chunk:
            continue
        # os.pathsep keeps compatibility with environment variables like /a:/b.
        for item in chunk.split(os.pathsep):
            item = item.strip()
            if item:
                parts.append(item)
    return parts
