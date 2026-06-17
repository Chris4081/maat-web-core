from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import time
from typing import Any

from .config import RuntimeSettings


def _total_memory_bytes() -> int | None:
    if platform.system() == "Darwin":
        try:
            completed = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if completed.returncode == 0:
                return int((completed.stdout or "").strip())
        except Exception:
            return None
    if hasattr(os, "sysconf"):
        try:
            pages = int(os.sysconf("SC_PHYS_PAGES"))
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            return pages * page_size
        except (OSError, ValueError, AttributeError):
            return None
    return None


def _run_text(command: list[str], timeout: float = 2.0) -> str:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        return ""
    if completed.returncode != 0:
        return ""
    return f"{completed.stdout or ''}\n{completed.stderr or ''}".strip()


def _linux_distro() -> str:
    try:
        data = {}
        with open("/etc/os-release", "r", encoding="utf-8") as handle:
            for line in handle:
                key, sep, value = line.strip().partition("=")
                if sep:
                    data[key] = value.strip().strip('"')
        return data.get("PRETTY_NAME") or data.get("NAME") or "Linux"
    except Exception:
        return "Linux"


def _linux_gpu_info() -> dict[str, Any]:
    if platform.system() != "Linux":
        return {"available": False, "kind": "none", "details": ""}

    details: list[str] = []
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        output = _run_text([nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"], timeout=3)
        if output:
            details.append(output.splitlines()[0].strip())
            return {"available": True, "kind": "nvidia", "details": " · ".join(details), "tool": "nvidia-smi"}
        return {"available": True, "kind": "nvidia", "details": "nvidia-smi gefunden", "tool": "nvidia-smi"}

    lspci = shutil.which("lspci")
    if lspci:
        output = _run_text([lspci], timeout=2)
        gpu_lines = [line for line in output.splitlines() if re.search(r"(vga|3d|display)", line, re.IGNORECASE)]
        text = "\n".join(gpu_lines)
        if re.search(r"nvidia", text, re.IGNORECASE):
            return {"available": True, "kind": "nvidia", "details": gpu_lines[0] if gpu_lines else "NVIDIA GPU", "tool": "lspci"}
        if re.search(r"(amd|radeon|ati)", text, re.IGNORECASE):
            return {"available": True, "kind": "amd", "details": gpu_lines[0] if gpu_lines else "AMD GPU", "tool": "lspci"}
        if re.search(r"intel", text, re.IGNORECASE):
            return {"available": True, "kind": "intel", "details": gpu_lines[0] if gpu_lines else "Intel GPU", "tool": "lspci"}

    if os.path.exists("/dev/dri"):
        return {"available": True, "kind": "drm", "details": "/dev/dri vorhanden", "tool": "devfs"}

    return {"available": False, "kind": "none", "details": ""}


def _recommended_model_for_memory(total_memory: int | None) -> dict[str, Any]:
    if not total_memory:
        return {"quant": "Q2", "ctx": 4096, "reason": "RAM unbekannt"}
    gb = total_memory / (1024 ** 3)
    if gb < 12:
        return {"quant": "kleineres Modell empfohlen", "ctx": 4096, "reason": "unter 12 GB RAM"}
    if gb < 20:
        return {"quant": "Q2", "ctx": 8192, "reason": "Intel/Linux 16 GB: konservativer CTX für ersten Test"}
    if gb < 24:
        return {"quant": "Q2", "ctx": 20000, "reason": "unter 24 GB RAM"}
    if gb < 32:
        return {"quant": "Q3", "ctx": 40000, "reason": "ab 24 GB RAM"}
    return {"quant": "Q4", "ctx": 40000, "reason": "ab 32 GB RAM"}


def _format_gb(value: int | None) -> str:
    if not value:
        return "unbekannt"
    return f"{value / (1024 ** 3):.1f} GB"


def _recommended_ctx_for_memory(total_memory: int | None) -> int:
    return int(_recommended_model_for_memory(total_memory)["ctx"])


def system_scan(settings: RuntimeSettings | None = None) -> dict[str, Any]:
    cpu_count = os.cpu_count() or 4
    system = platform.system()
    machine = platform.machine()
    processor = platform.processor()
    total_memory = _total_memory_bytes()
    apple_silicon = system == "Darwin" and machine == "arm64"
    darwin_intel = system == "Darwin" and machine in {"x86_64", "amd64"}
    linux = system == "Linux"
    linux_gpu = _linux_gpu_info() if linux else {"available": False, "kind": "none", "details": ""}
    model_recommendation = _recommended_model_for_memory(total_memory)

    if apple_silicon:
        threads = max(4, min(cpu_count - 2 if cpu_count > 6 else cpu_count, 10))
        gpu_layers = 999
        profile = "mac_arm_metal"
        rationale = "Apple Silicon erkannt: Metal-Offload bevorzugen, CPU-Threads konservativ unter Vollauslastung halten."
    elif darwin_intel:
        threads = max(2, min(cpu_count - 1 if cpu_count > 2 else cpu_count, 8))
        gpu_layers = 0
        profile = "mac_intel_cpu"
        rationale = "Intel-macOS erkannt: CPU-Modus bevorzugen, GPU-Layers aus lassen."
    elif linux:
        threads = max(2, min(cpu_count - 1 if cpu_count > 2 else cpu_count, 12))
        if linux_gpu.get("kind") == "nvidia":
            gpu_layers = 999
            profile = "linux_nvidia_candidate"
            rationale = "Linux mit NVIDIA erkannt: GPU-Offload ist sinnvoll, wenn llama-cpp-python mit CUDA/Vulkan gebaut ist."
        elif linux_gpu.get("kind") in {"amd", "intel", "drm"}:
            gpu_layers = 0
            profile = f"linux_{linux_gpu.get('kind')}_cpu_safe"
            rationale = "Linux-GPU erkannt, aber sichere Auto-Einstellung bleibt CPU. Für Vulkan/ROCm-Build GPU-Layers manuell testen."
        else:
            gpu_layers = 0
            profile = "linux_cpu"
            rationale = "Linux ohne eindeutig nutzbare GPU erkannt: sichere CPU-Startwerte."
    else:
        threads = max(2, min(cpu_count - 1 if cpu_count > 2 else cpu_count, 12))
        gpu_layers = 0
        profile = "generic_cpu"
        rationale = "Generisches System: sichere CPU-Startwerte ohne GPU-Annahme."

    ctx_recommendation = _recommended_ctx_for_memory(total_memory)
    current_ctx = int(getattr(settings, "llama_n_ctx", 4096) or 4096) if settings else ctx_recommendation
    notes = [
        rationale,
        "CTX wird bewusst nicht automatisch überschrieben, damit du ihn je Modell frei setzen kannst.",
        f"Modell/RAM-Empfehlung: {model_recommendation['quant']} mit CTX {model_recommendation['ctx']} ({model_recommendation['reason']}).",
    ]
    if linux:
        notes.append(f"Linux-Distribution: {_linux_distro()}.")
        if linux_gpu.get("details"):
            notes.append(f"GPU-Erkennung: {linux_gpu.get('kind')} · {linux_gpu.get('details')}.")
        notes.append("Linux-TTS: optional speech-dispatcher/spd-say oder espeak-ng installieren.")
        if linux_gpu.get("kind") == "nvidia":
            notes.append("Falls Generation mit GPU-Layers fehlschlägt: llama-cpp-python CUDA/Vulkan-Build prüfen oder GPU Layers auf 0 setzen.")
    if total_memory:
        gb = total_memory / (1024 ** 3)
        if gb < 20:
            notes.append("16-GB-Klasse erkannt: für große MoE/GGUF-Modelle zunächst Q2 und niedrigeren CTX testen.")
        if current_ctx > ctx_recommendation * 2 and gb < 36:
            notes.append("Der aktuelle CTX ist deutlich höher als die RAM-Empfehlung; falls es langsam wird, CTX senken.")
    return {
        "ok": True,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "profile": profile,
        "system": system,
        "machine": machine,
        "processor": processor,
        "distro": _linux_distro() if linux else "",
        "gpu": linux_gpu,
        "cpu_count": cpu_count,
        "memory_bytes": total_memory,
        "memory": _format_gb(total_memory),
        "recommended": {
            "llama_n_threads": int(threads),
            "llama_n_gpu_layers": int(gpu_layers),
            "ctx_recommendation": int(ctx_recommendation),
            "model_quant": str(model_recommendation["quant"]),
            "model_ctx": int(model_recommendation["ctx"]),
        },
        "current": {
            "loader_tuning_mode": getattr(settings, "loader_tuning_mode", "manual") if settings else "manual",
            "llama_n_ctx": int(getattr(settings, "llama_n_ctx", current_ctx) or current_ctx) if settings else current_ctx,
            "llama_n_threads": int(getattr(settings, "llama_n_threads", threads) or threads) if settings else threads,
            "llama_n_gpu_layers": int(getattr(settings, "llama_n_gpu_layers", gpu_layers) or 0) if settings else gpu_layers,
        },
        "notes": notes,
    }


def apply_auto_loader_settings(settings: RuntimeSettings) -> dict[str, Any]:
    scan = system_scan(settings)
    recommended = scan.get("recommended") or {}
    settings.loader_tuning_mode = "auto"
    if "llama_n_threads" in recommended:
        settings.llama_n_threads = int(recommended["llama_n_threads"])
    if "llama_n_gpu_layers" in recommended:
        settings.llama_n_gpu_layers = int(recommended["llama_n_gpu_layers"])
    settings.loader_scan_result = scan
    return scan


def effective_loader_values(settings: RuntimeSettings) -> dict[str, int | str]:
    mode = str(getattr(settings, "loader_tuning_mode", "manual") or "manual").lower()
    if mode == "auto":
        scan = system_scan(settings)
        recommended = scan.get("recommended") or {}
        return {
            "loader_tuning_mode": "auto",
            "llama_n_ctx": int(getattr(settings, "llama_n_ctx", 4096) or 4096),
            "llama_n_threads": int(recommended.get("llama_n_threads") or getattr(settings, "llama_n_threads", 8) or 8),
            "llama_n_gpu_layers": int(recommended.get("llama_n_gpu_layers") or 0),
        }
    return {
        "loader_tuning_mode": "manual",
        "llama_n_ctx": int(getattr(settings, "llama_n_ctx", 4096) or 4096),
        "llama_n_threads": int(getattr(settings, "llama_n_threads", 8) or 8),
        "llama_n_gpu_layers": int(getattr(settings, "llama_n_gpu_layers", 0) or 0),
    }
