from __future__ import annotations

import asyncio
import gc
import inspect
import time
from collections.abc import AsyncIterator
from pathlib import Path
from threading import Lock
from typing import Any


_MODEL_CACHE: dict[str, Any] = {}
_CACHE_LOCK = Lock()


def _log(message: str) -> None:
    print(f"[MAAT Web Core][llama.cpp] {message}", flush=True)


def _format_size(size: int) -> str:
    value = float(size)
    units = ["B", "KB", "MB", "GB", "TB"]
    unit = 0
    while value >= 1024 and unit < len(units) - 1:
        value /= 1024
        unit += 1
    return f"{value:.1f} {units[unit]}" if unit else f"{int(value)} {units[unit]}"


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "an"}


def _model_family(options: dict[str, Any]) -> str:
    name = Path(str(options.get("llama_model_path") or "")).name.lower()
    if "qwen" in name:
        return "qwen"
    if "gemma" in name:
        return "gemma"
    if "lfm" in name or "liquid" in name:
        return "lfm"
    return "generic"


def _is_lfm2_model(options: dict[str, Any]) -> bool:
    name = Path(str(options.get("llama_model_path") or "")).name.lower()
    return any(marker in name for marker in ("lfm2", "lfm-2", "lfm_2", "liquid2", "liquid-2"))


def _effective_n_ctx(options: dict[str, Any]) -> tuple[int, int, str]:
    configured = max(512, _as_int(options.get("llama_n_ctx"), 4096))
    requested = max(512, _as_int(options.get("llama_n_ctx_requested"), configured))
    if options.get("llama_n_ctx_reason"):
        return configured, requested, str(options.get("llama_n_ctx_reason"))
    family = _model_family(options)
    if family == "gemma" and _as_bool(options.get("llama_gemma_safe_ctx"), False):
        # Optional emergency mode for machines/builds that cannot allocate
        # Gemma's large SWA/KV cache.  Default stays full requested context.
        cap = max(512, _as_int(options.get("llama_gemma_ctx_cap"), 8192))
        if configured > cap:
            return cap, requested, f"gemma_safe_ctx_cap:{cap}"
    if family == "lfm" and _is_lfm2_model(options):
        # LFM2 is published as a local/edge model family with 32K context.
        # Keep user settings intact in llama_n_ctx_requested, but avoid trying
        # to allocate beyond the advertised train/context window by default.
        cap = max(512, _as_int(options.get("llama_lfm2_ctx_cap"), 32768))
        if configured > cap:
            return cap, requested, f"lfm2_ctx_cap:{cap}"
    return configured, requested, "requested"


def normalize_options_for_model(options: dict[str, Any]) -> dict[str, Any]:
    """Return options adjusted for the selected GGUF model family.

    The caller can still keep the user's configured context separately; this
    normalizes the values that should actually be used for prompt budgeting and
    llama.cpp loading.
    """
    normalized = dict(options)
    ctx_effective, ctx_requested, ctx_reason = _effective_n_ctx(normalized)
    normalized["llama_n_ctx"] = ctx_effective
    normalized["llama_n_ctx_requested"] = ctx_requested
    normalized["llama_n_ctx_reason"] = ctx_reason
    normalized["llama_model_family"] = _model_family(normalized)
    normalized["llama_flash_attn"] = _flash_attn_requested(normalized)
    return normalized


def _flash_attn_requested(options: dict[str, Any]) -> bool:
    if "llama_flash_attn" in options:
        return _as_bool(options.get("llama_flash_attn"))
    return _model_family(options) in {"gemma", "lfm"}


def _swa_full_requested(options: dict[str, Any]) -> bool | None:
    if "llama_swa_full" in options:
        return _as_bool(options.get("llama_swa_full"))
    if _model_family(options) == "gemma":
        # Gemma SWA with a full-size cache can explode memory at 40k+ ctx on
        # Apple Silicon.  Sliding-window cache keeps the advertised context
        # usable without allocating the full train-context KV layout.
        return False
    return None


def _n_batch_values(options: dict[str, Any]) -> tuple[int, int]:
    family = _model_family(options)
    default_batch = 512
    default_ubatch = 256 if family in {"gemma", "lfm"} else 512
    n_batch = max(32, _as_int(options.get("llama_n_batch"), default_batch))
    n_ubatch = max(32, _as_int(options.get("llama_n_ubatch"), default_ubatch))
    return n_batch, min(n_batch, n_ubatch)


def _supports_parameter(callable_obj: Any, parameter_name: str) -> bool:
    try:
        return parameter_name in inspect.signature(callable_obj).parameters
    except (TypeError, ValueError):
        return False


def _compat_lines(options: dict[str, Any], *, llama_class: Any | None = None) -> list[str]:
    family = _model_family(options)
    ctx_effective, ctx_requested, ctx_reason = _effective_n_ctx(options)
    flash_requested = _flash_attn_requested(options)
    flash_supported = None
    if llama_class is not None:
        flash_supported = _supports_parameter(llama_class.__init__, "flash_attn")
    if flash_supported is None:
        flash_value = "auto-on" if flash_requested else "off"
    elif flash_requested and flash_supported:
        flash_value = "on"
    elif flash_requested and not flash_supported:
        flash_value = "unsupported-by-llama-cpp-python"
    else:
        flash_value = "off"
    n_batch, n_ubatch = _n_batch_values(options)
    swa_full = _swa_full_requested(options)
    return [
        f"family={family}",
        f"ctx_requested={ctx_requested}",
        f"ctx_effective={ctx_effective}",
        f"ctx_reason={ctx_reason}",
        f"flash_attn={flash_value}",
        f"swa_full={'auto' if swa_full is None else str(swa_full).lower()}",
        f"n_batch={n_batch}",
        f"n_ubatch={n_ubatch}",
        f"thinking_arg={'enabled' if family in {'qwen', 'gemma'} else 'skipped'}",
    ]


def _cache_key(options: dict[str, Any]) -> str:
    ctx_effective, _, _ = _effective_n_ctx(options)
    return "|".join(
        [
            str(options.get("llama_model_path", "")),
            str(ctx_effective),
            str(_as_int(options.get("llama_n_threads"), 4)),
            str(_as_int(options.get("llama_n_gpu_layers"), 0)),
            f"flash={_flash_attn_requested(options)}",
            f"swa_full={_swa_full_requested(options)}",
            f"batch={_n_batch_values(options)}",
            f"family={_model_family(options)}",
        ]
    )


def clear_model_cache(reason: str = "") -> int:
    with _CACHE_LOCK:
        models = list(_MODEL_CACHE.values())
        _MODEL_CACHE.clear()
    closed = 0
    for model in models:
        close = getattr(model, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
        closed += 1
    if closed:
        suffix = f" ({reason})" if reason else ""
        _log(f"Modell-Cache geleert: {closed} Eintrag{'e' if closed != 1 else ''}{suffix}")
        gc.collect()
    return closed


def _drop_cache(options: dict[str, Any]) -> None:
    key = _cache_key(options)
    with _CACHE_LOCK:
        _MODEL_CACHE.pop(key, None)


def _decode_retry_options(options: dict[str, Any]) -> list[dict[str, Any]]:
    family = _model_family(options)
    if family not in {"gemma", "lfm"}:
        return []
    current_ctx, requested_ctx, _ = _effective_n_ctx(options)
    candidates = [32768, 24576, 16384, 8192]
    retries: list[dict[str, Any]] = []
    for ctx in candidates:
        if ctx >= current_ctx:
            continue
        retry = dict(options)
        retry["llama_n_ctx"] = ctx
        retry["llama_n_ctx_requested"] = requested_ctx
        retry["llama_n_ctx_reason"] = f"{family}_decode_retry:{ctx}"
        retry["llama_flash_attn"] = True
        if family == "gemma":
            retry["llama_swa_full"] = False
        retry["llama_n_ubatch"] = min(_n_batch_values(options)[1], 128)
        retries.append(normalize_options_for_model(retry))
    return retries


def _is_decode_memory_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "llama_decode returned -3" in text or "decode returned -3" in text


def _load_llama(options: dict[str, Any]):
    try:
        from llama_cpp import Llama
    except Exception as exc:
        raise RuntimeError(
            "llama-cpp-python ist nicht installiert. Installiere es im Python-Environment "
            "oder nutze den OpenAI-kompatiblen llama.cpp Server-Adapter."
        ) from exc

    model_path = Path(str(options.get("llama_model_path") or "")).expanduser()
    if not model_path.exists():
        raise FileNotFoundError(f"GGUF-Modell nicht gefunden: {model_path}")

    key = _cache_key(options)
    ctx_effective, ctx_requested, ctx_reason = _effective_n_ctx(options)
    threads = _as_int(options.get("llama_n_threads"), 4)
    gpu_layers = _as_int(options.get("llama_n_gpu_layers"), 0)
    flash_requested = _flash_attn_requested(options)
    swa_full_requested = _swa_full_requested(options)
    n_batch, n_ubatch = _n_batch_values(options)
    flash_supported = _supports_parameter(Llama.__init__, "flash_attn")
    swa_supported = _supports_parameter(Llama.__init__, "swa_full")
    with _CACHE_LOCK:
        if key in _MODEL_CACHE:
            _log(f"Cache-Hit: {model_path.name}")
        else:
            started = time.perf_counter()
            try:
                size = _format_size(model_path.stat().st_size)
            except OSError:
                size = "unbekannte Größe"
            _log(
                "Lade GGUF-Modell: "
                f"{model_path.name} ({size}) | "
                f"family={_model_family(options)} | "
                f"ctx={ctx_effective}"
                f"{f' (requested {ctx_requested}, {ctx_reason})' if ctx_effective != ctx_requested else ''} | "
                f"threads={threads} | "
                f"gpu_layers={gpu_layers} | "
                f"flash_attn={'on' if flash_requested and flash_supported else 'off'}"
                f"{' (unsupported)' if flash_requested and not flash_supported else ''} | "
                f"swa_full={'auto' if swa_full_requested is None else str(swa_full_requested).lower()}"
                f"{' (unsupported)' if swa_full_requested is not None and not swa_supported else ''} | "
                f"n_batch={n_batch} | n_ubatch={n_ubatch}"
            )
            load_kwargs: dict[str, Any] = {
                "model_path": str(model_path),
                "n_ctx": ctx_effective,
                "n_batch": n_batch,
                "n_ubatch": n_ubatch,
                "n_threads": threads,
                "n_threads_batch": threads,
                "n_gpu_layers": gpu_layers,
                "logits_all": False,
                "embedding": False,
                "verbose": False,
            }
            if flash_requested and flash_supported:
                load_kwargs["flash_attn"] = True
            if swa_full_requested is not None and swa_supported:
                load_kwargs["swa_full"] = swa_full_requested
            try:
                _MODEL_CACHE[key] = Llama(**load_kwargs)
            except Exception as exc:
                if not load_kwargs.get("flash_attn"):
                    raise
                _log(f"Flash-Attention Load-Retry ohne flash_attn: {exc}")
                load_kwargs.pop("flash_attn", None)
                _MODEL_CACHE[key] = Llama(**load_kwargs)
            elapsed = time.perf_counter() - started
            _log(f"Modell geladen und im RAM-Cache: {model_path.name} ({elapsed:.2f}s)")
        return _MODEL_CACHE[key]


def _create_chat_completion(llama: Any, messages: list[dict[str, str]], options: dict[str, Any]):
    """Call llama.cpp's chat handler with model-family thinking kwargs."""
    try:
        from llama_cpp import llama_chat_format

        handler = (
            getattr(llama, "chat_handler", None)
            or getattr(llama, "_chat_handlers", {}).get(getattr(llama, "chat_format", None))
            or llama_chat_format.get_chat_completion_handler(getattr(llama, "chat_format", None))
        )
        completion_kwargs: dict[str, Any] = {
            "llama": llama,
            "messages": messages,
            "temperature": float(options.get("temperature", 0.7)),
            "top_p": float(options.get("top_p", 0.9)),
            "top_k": _as_int(options.get("top_k"), 20),
            "min_p": float(options.get("min_p", 0.0)),
            "max_tokens": _as_int(options.get("max_tokens"), 512),
            "stream": True,
        }
        family = _model_family(options)
        if family in {"qwen", "gemma"}:
            completion_kwargs["enable_thinking"] = bool(options.get("enable_thinking", False))
        try:
            return handler(**completion_kwargs)
        except TypeError as exc:
            if "enable_thinking" not in completion_kwargs:
                raise
            _log(f"Chat-Template unterstützt enable_thinking nicht direkt, retry ohne Flag: {exc}")
            completion_kwargs.pop("enable_thinking", None)
            if family == "gemma" and bool(options.get("enable_thinking", False)):
                completion_kwargs["messages"] = [{"role": "system", "content": "<|think|>"}, *messages]
                _log("Gemma Thinking-Fallback: <|think|>-Systemturn vorangestellt")
            return handler(**completion_kwargs)
    except TypeError as exc:
        _log(f"Chat-Template-Option nicht unterstützt, fallback: {exc}")
        return llama.create_chat_completion(
            messages=messages,
            temperature=float(options.get("temperature", 0.7)),
            top_p=float(options.get("top_p", 0.9)),
            max_tokens=_as_int(options.get("max_tokens"), 512),
            stream=True,
        )


class LlamaCppDirectAdapter:
    """Direct llama-cpp-python GGUF loader inspired by the MAAT-RPG llama backend."""

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        options: dict[str, Any],
    ) -> AsyncIterator[str | dict[str, Any]]:
        queue: asyncio.Queue[tuple[str, str | dict[str, Any] | None]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def worker() -> None:
            try:
                model_name = Path(str(options.get("llama_model_path") or "")).name or "GGUF"
                model_path = Path(str(options.get("llama_model_path") or "")).expanduser()
                cache_key = _cache_key(options)
                cache_hit = cache_key in _MODEL_CACHE
                try:
                    size = _format_size(model_path.stat().st_size)
                except OSError:
                    size = "unbekannte Größe"
                ctx_effective, ctx_requested, ctx_reason = _effective_n_ctx(options)
                threads = _as_int(options.get("llama_n_threads"), 4)
                gpu_layers = _as_int(options.get("llama_n_gpu_layers"), 0)
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    (
                        "event",
                        {
                            "event": "log",
                            "data": {
                                "source": "model",
                                "title": "llama.cpp Direct · Modell",
                                "lines": [
                                    f"model={model_name}",
                                    f"path={model_path}",
                                    f"size={size}",
                                    f"cache={'hit' if cache_hit else 'miss'}",
                                    f"loader={options.get('loader_tuning_mode') or 'manual'} ctx={ctx_effective} threads={threads} gpu_layers={gpu_layers}",
                                    *_compat_lines(options),
                                ],
                            },
                        },
                    ),
                )
                _log(
                    "Generation vorbereitet: "
                    f"model={model_name} | messages={len(messages)} | "
                    f"ctx={ctx_effective}/{ctx_requested} ({ctx_reason}) | "
                    f"max_tokens={_as_int(options.get('max_tokens'), 512)} | "
                    f"temp={float(options.get('temperature', 0.7)):.2f} | "
                    f"top_p={float(options.get('top_p', 0.9)):.2f}"
                )
                attempt_options = [options, *_decode_retry_options(options)]
                started = time.perf_counter()
                chunks = 0
                chars = 0
                used_options = options
                last_error: Exception | None = None

                for attempt_index, current_options in enumerate(attempt_options, 1):
                    used_options = current_options
                    current_ctx, current_requested, current_reason = _effective_n_ctx(current_options)
                    attempt_family = _model_family(current_options)
                    family_title = "Gemma" if attempt_family == "gemma" else "LFM" if attempt_family == "lfm" else attempt_family
                    if attempt_index > 1:
                        _log(
                            f"{family_title} Decode-Retry: "
                            f"ctx={current_ctx}/{current_requested} ({current_reason})"
                        )
                        retry_lines = [
                            "Der Decode ist beim vorherigen Kontext gekippt.",
                            f"retry={attempt_index - 1} ctx={current_ctx} requested={current_requested}",
                            f"reason={current_reason}",
                            "flash_attn=on n_ubatch=128",
                        ]
                        if attempt_family == "gemma":
                            retry_lines.append("swa_full=false")
                        loop.call_soon_threadsafe(
                            queue.put_nowait,
                            (
                                "event",
                                {
                                    "event": "log",
                                    "data": {
                                        "source": "model",
                                        "title": f"{family_title} Stabilitäts-Retry",
                                        "lines": retry_lines,
                                    },
                                },
                            ),
                        )

                    attempt_started = time.perf_counter()
                    llama = _load_llama(current_options)
                    load_elapsed = time.perf_counter() - attempt_started
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        (
                            "event",
                            {
                                "event": "log",
                                "data": {
                                    "source": "model",
                                    "title": "llama.cpp Direct · Modell bereit",
                                    "lines": [
                                        f"model={model_name}",
                                        f"cache={'hit' if attempt_index == 1 and cache_hit else 'retry/cache'}",
                                        f"ctx={current_ctx}/{current_requested} ({current_reason})",
                                        f"bereit_nach={load_elapsed:.2f}s",
                                    ],
                                },
                            },
                        ),
                    )
                    prompt_started = time.perf_counter()
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        (
                            "event",
                            {
                                "event": "log",
                                "data": {
                                    "source": "progress",
                                    "title": "Prompt Processing gestartet",
                                    "lines": [
                                        f"model={model_name}",
                                        f"ctx={current_ctx}/{current_requested} ({current_reason})",
                                        "llama.cpp verarbeitet jetzt den Prompt; erstes Token kommt nach Prompt-Eval.",
                                    ],
                                },
                            },
                        ),
                    )
                    chunks = 0
                    chars = 0
                    try:
                        stream = _create_chat_completion(llama, messages, current_options)
                        for packet in stream:
                            choices = packet.get("choices") or []
                            if not choices:
                                continue
                            delta = choices[0].get("delta") or {}
                            chunk = delta.get("content")
                            if chunk:
                                if chunks == 0:
                                    first_token_elapsed = time.perf_counter() - prompt_started
                                    loop.call_soon_threadsafe(
                                        queue.put_nowait,
                                        (
                                            "event",
                                            {
                                                "event": "log",
                                                "data": {
                                                    "source": "progress",
                                                    "title": "Prompt Processing fertig",
                                                    "lines": [
                                                        f"erstes_token_nach={first_token_elapsed:.2f}s",
                                                        f"model={model_name}",
                                                        f"ctx={current_ctx}",
                                                    ],
                                                },
                                            },
                                        ),
                                    )
                                chunks += 1
                                chars += len(str(chunk))
                                loop.call_soon_threadsafe(queue.put_nowait, ("token", str(chunk)))
                        last_error = None
                        break
                    except Exception as exc:
                        last_error = exc
                        _drop_cache(current_options)
                        if chunks > 0 or not _is_decode_memory_error(exc) or attempt_index >= len(attempt_options):
                            raise
                        _log(f"{family_title} Decode fehlgeschlagen, versuche kleineren Kontext: {exc}")

                if last_error is not None:
                    raise last_error

                elapsed = time.perf_counter() - started
                used_ctx, used_requested, used_reason = _effective_n_ctx(used_options)
                _log(
                    "Generation fertig: "
                    f"model={model_name} | ctx={used_ctx}/{used_requested} ({used_reason}) | "
                    f"chunks={chunks} | chars={chars} | {elapsed:.2f}s"
                )
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    (
                        "event",
                        {
                            "event": "log",
                            "data": {
                                "source": "generation",
                                "title": "Generation fertig",
                                "lines": [
                                    f"model={model_name}",
                                    f"ctx={used_ctx}/{used_requested} ({used_reason})",
                                    f"chunks={chunks} chars={chars}",
                                    f"gesamtzeit={elapsed:.2f}s",
                                ],
                            },
                        },
                    ),
                )
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
            except Exception as exc:
                _log(f"Fehler: {exc}")
                loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))

        worker_task = asyncio.create_task(asyncio.to_thread(worker))
        try:
            while True:
                kind, payload = await queue.get()
                if kind == "token" and payload:
                    yield str(payload)
                elif kind == "event" and isinstance(payload, dict):
                    yield payload
                elif kind == "error":
                    raise RuntimeError(payload or "llama.cpp generation failed")
                elif kind == "done":
                    break
        finally:
            if worker_task.done():
                await worker_task
