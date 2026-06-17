#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

MODELS_DIR="$ROOT_DIR/models"
WIKI_DIR="$ROOT_DIR/wiki"
DATA_DIR="$ROOT_DIR/data"
SETTINGS_PATH="$DATA_DIR/settings.json"

mkdir -p "$MODELS_DIR" "$WIKI_DIR" "$DATA_DIR"

MODEL_REPO="unsloth/gemma-4-26B-A4B-it-GGUF"
MODEL_Q2_NAME="gemma-4-26B-A4B-it-UD-Q2_K_XL.gguf"
MODEL_Q3_NAME="gemma-4-26B-A4B-it-UD-Q3_K_XL.gguf"
MODEL_Q4_NAME="gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf"
MODEL_Q2_URL="https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF/resolve/main/${MODEL_Q2_NAME}?download=true"
MODEL_Q3_URL="https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF/resolve/main/${MODEL_Q3_NAME}?download=true"
MODEL_Q4_URL="https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF/resolve/main/${MODEL_Q4_NAME}?download=true"

ZIM_NAME="wikipedia_de_all_mini_2026-04.zim"
ZIM_URL="https://download.kiwix.org/zim/wikipedia/${ZIM_NAME}"

ask_yes_no() {
  local prompt="$1"
  local default="${2:-n}"
  local answer=""
  local suffix="[y/N]"
  if [[ "$default" == "y" ]]; then
    suffix="[Y/n]"
  fi
  read -r -p "${prompt} ${suffix}: " answer
  answer="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"
  if [[ -z "$answer" ]]; then
    answer="$default"
  fi
  [[ "$answer" == "y" || "$answer" == "yes" || "$answer" == "j" || "$answer" == "ja" ]]
}

ram_gb() {
  local bytes=""
  if command -v sysctl >/dev/null 2>&1; then
    bytes="$(sysctl -n hw.memsize 2>/dev/null || true)"
  fi
  if [[ -z "$bytes" && -r /proc/meminfo ]]; then
    local kb
    kb="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
    bytes="$((kb * 1024))"
  fi
  if [[ -z "$bytes" ]]; then
    echo 0
    return
  fi
  echo "$(( (bytes + 1073741823) / 1073741824 ))"
}

install_hint_latex() {
  local os_name
  os_name="$(uname -s 2>/dev/null || echo unknown)"
  echo ""
  echo "LaTeX/PDF-Pruefung"
  echo "=================="
  if command -v pdflatex >/dev/null 2>&1; then
    echo "pdflatex gefunden: $(command -v pdflatex)"
    return
  fi

  echo "pdflatex wurde nicht gefunden."
  echo "Der Chat funktioniert trotzdem, aber .tex -> PDF im Docs/File-Builder braucht eine LaTeX-Installation."

  if [[ "$os_name" == "Linux" ]]; then
    echo ""
    echo "Empfohlen fuer Debian/Ubuntu:"
    echo "  sudo apt install texlive-latex-base texlive-latex-recommended texlive-fonts-recommended"
    echo ""
    echo "Fuer groessere Paper zusaetzlich:"
    echo "  sudo apt install texlive-latex-extra"
    if command -v apt >/dev/null 2>&1 && command -v sudo >/dev/null 2>&1; then
      if ask_yes_no "LaTeX-Basispakete jetzt per apt installieren?" "n"; then
        if sudo apt update; then
          sudo apt install -y texlive-latex-base texlive-latex-recommended texlive-fonts-recommended || true
        else
          echo ""
          echo "apt update ist fehlgeschlagen. Das Setup laeuft weiter."
          echo "Bitte pruefe die Paketquellen deiner Distribution und installiere LaTeX spaeter manuell."
          echo "Installiere LaTeX spaeter manuell, z.B.:"
          echo "  sudo apt install texlive-latex-base texlive-latex-recommended texlive-fonts-recommended"
        fi
      fi
      if ! command -v pdflatex >/dev/null 2>&1; then
        echo "Hinweis: pdflatex ist nach der Installation noch nicht im PATH oder die Installation ist fehlgeschlagen."
      fi
    else
      echo "apt/sudo nicht gefunden. Bitte installiere LaTeX mit dem Paketmanager deiner Distribution."
    fi
  elif [[ "$os_name" == "Darwin" ]]; then
    echo ""
    echo "macOS-Optionen:"
    echo "  brew install --cask mactex-no-gui"
    echo "oder kleiner:"
    echo "  brew install --cask basictex"
    echo ""
    echo "Nach BasicTeX ggf. Terminal neu starten und fehlende Pakete mit tlmgr nachinstallieren."
  else
    echo ""
    echo "Installiere eine TeX-Distribution fuer dein System, z.B. TeX Live oder MiKTeX."
  fi
}

install_llama_cpp_python() {
  local os_name machine build_target install_default
  os_name="$(uname -s 2>/dev/null || echo unknown)"
  machine="$(uname -m 2>/dev/null || echo unknown)"
  build_target="${MAAT_LLAMA_CPP_BUILD:-auto}"
  install_default="y"

  echo ""
  echo "llama.cpp Direct Loader"
  echo "======================="
  if python - <<'PY' >/dev/null 2>&1
import llama_cpp  # noqa: F401
PY
  then
    echo "llama-cpp-python ist bereits installiert."
    return
  fi

  echo "llama-cpp-python ist noch nicht installiert."
  echo "Der OpenAI/API-Adapter funktioniert ohne dieses Paket."
  echo "Der direkte GGUF-Loader im Web Core braucht es aber."
  echo ""
  echo "Build-Ziel:"
  echo "  MAAT_LLAMA_CPP_BUILD=cpu     ./setup.sh"
  echo "  MAAT_LLAMA_CPP_BUILD=metal   ./setup.sh"
  echo "  MAAT_LLAMA_CPP_BUILD=cuda    ./setup.sh"
  echo "  MAAT_LLAMA_CPP_BUILD=vulkan  ./setup.sh"
  echo ""
  echo "Standard: Apple Silicon -> metal, sonst CPU-safe."

  if ! ask_yes_no "llama-cpp-python fuer direkten GGUF-Loader installieren?" "$install_default"; then
    echo "llama-cpp-python uebersprungen. Nutze dann den OpenAI-kompatiblen API-Adapter oder installiere es spaeter."
    return
  fi

  if [[ "$build_target" == "auto" ]]; then
    if [[ "$os_name" == "Darwin" && "$machine" == "arm64" ]]; then
      build_target="metal"
    else
      build_target="cpu"
    fi
    if [[ "$os_name" == "Linux" && -n "$(command -v nvidia-smi || true)" ]]; then
      echo "NVIDIA wurde erkannt. CPU-safe bleibt Standard."
      if ask_yes_no "Statt CPU einen CUDA-Build versuchen? CUDA Toolkit muss installiert sein." "n"; then
        build_target="cuda"
      fi
    fi
  fi

  echo "Installiere llama-cpp-python mit Build-Ziel: $build_target"
  case "$build_target" in
    metal)
      CMAKE_ARGS="-DGGML_METAL=on" FORCE_CMAKE=1 python -m pip install --upgrade --force-reinstall --no-cache-dir llama-cpp-python
      ;;
    cuda)
      CMAKE_ARGS="-DGGML_CUDA=on" FORCE_CMAKE=1 python -m pip install --upgrade --force-reinstall --no-cache-dir llama-cpp-python
      ;;
    vulkan)
      CMAKE_ARGS="-DGGML_VULKAN=on" FORCE_CMAKE=1 python -m pip install --upgrade --force-reinstall --no-cache-dir llama-cpp-python
      ;;
    cpu)
      python -m pip install --upgrade llama-cpp-python
      ;;
    *)
      echo "Unbekanntes MAAT_LLAMA_CPP_BUILD='$build_target'. Erlaubt: auto, cpu, metal, cuda, vulkan."
      return 1
      ;;
  esac

  if python - <<'PY' >/dev/null 2>&1
import llama_cpp  # noqa: F401
PY
  then
    echo "llama-cpp-python erfolgreich installiert."
  else
    echo "WARNUNG: llama-cpp-python konnte nach der Installation nicht importiert werden."
    echo "Du kannst weiterhin den OpenAI-kompatiblen API-Adapter nutzen."
  fi
}

download_file() {
  local url="$1"
  local dest="$2"
  local label="$3"
  if [[ -f "$dest" ]]; then
    echo "Bereits vorhanden: $dest"
    return
  fi
  echo "Download: $label"
  echo "Ziel: $dest"
  if command -v curl >/dev/null 2>&1; then
    curl -L --fail --continue-at - --output "$dest" "$url"
  else
    python3 - "$url" "$dest" <<'PY'
import sys
import urllib.request

url, dest = sys.argv[1], sys.argv[2]
with urllib.request.urlopen(url) as response, open(dest, "wb") as handle:
    while True:
        chunk = response.read(1024 * 1024)
        if not chunk:
            break
        handle.write(chunk)
PY
  fi
}

write_settings() {
  local model_path="${1:-}"
  local ctx="${2:-}"
  local zim_path="${3:-}"
  python3 - "$SETTINGS_PATH" "$MODELS_DIR" "$model_path" "$ctx" "$zim_path" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
models_dir = Path(sys.argv[2])
model_path = sys.argv[3]
ctx = sys.argv[4]
zim_path = sys.argv[5]

settings = {}
if settings_path.exists():
    try:
        loaded = json.loads(settings_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            settings.update(loaded)
    except Exception:
        pass

settings["gguf_model_dirs_custom"] = str(models_dir)

if model_path:
    settings.update(
        {
            "model_adapter": "llama_cpp_direct",
            "model_name": Path(model_path).name,
            "llama_model_path": str(Path(model_path)),
            "favorite_model_paths": [str(Path(model_path))],
        }
    )
    if ctx:
        settings["llama_n_ctx"] = int(ctx)
        settings["max_tokens_from_ctx"] = True

if zim_path:
    settings.update(
        {
            "offline_wiki_enabled": True,
            "offline_wiki_auto": True,
            "offline_wiki_zim_path": str(Path(zim_path)),
        }
    )

settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Settings geschrieben: {settings_path}")
PY
}

echo ""
echo "MAAT Web Core Setup"
echo "==================="
echo ""
echo "Hinweis:"
echo "- Modelle werden NICHT mit dem Repo ausgeliefert."
echo "- Gemma 4 GGUF wird optional direkt von Hugging Face geladen."
echo "- Wikipedia ZIM wird optional direkt von Kiwix geladen."
echo "- Bitte beachte die jeweiligen Lizenzen und Nutzungsbedingungen."
echo ""

if [[ ! -d ".venv" ]]; then
  echo "Erstelle lokale Python-Umgebung: .venv"
  python3 -m venv .venv
fi

source ".venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

install_llama_cpp_python
install_hint_latex

RAM_GB="$(ram_gb)"
echo ""
echo "Erkannter RAM: ${RAM_GB} GB"

MODEL_NAME="$MODEL_Q2_NAME"
MODEL_URL="$MODEL_Q2_URL"
MODEL_CTX="20000"
MODEL_LABEL="Gemma 4 26B A4B Q2 · ctx 20k"

if (( RAM_GB >= 32 )); then
  MODEL_NAME="$MODEL_Q4_NAME"
  MODEL_URL="$MODEL_Q4_URL"
  MODEL_CTX="40000"
  MODEL_LABEL="Gemma 4 26B A4B Q4 · ctx 40k"
elif (( RAM_GB >= 24 )); then
  MODEL_NAME="$MODEL_Q3_NAME"
  MODEL_URL="$MODEL_Q3_URL"
  MODEL_CTX="40000"
  MODEL_LABEL="Gemma 4 26B A4B Q3 · ctx 40k"
fi

MODEL_PATH="$MODELS_DIR/$MODEL_NAME"
echo "Empfohlenes Modell: $MODEL_LABEL"

DOWNLOADED_MODEL=""
if ask_yes_no "Empfohlenes Gemma-4-GGUF herunterladen?" "n"; then
  download_file "$MODEL_URL" "$MODEL_PATH" "$MODEL_LABEL"
  DOWNLOADED_MODEL="$MODEL_PATH"
fi

DOWNLOADED_ZIM=""
if ask_yes_no "Deutsche Offline-Wikipedia-ZIM herunterladen?" "n"; then
  download_file "$ZIM_URL" "$WIKI_DIR/$ZIM_NAME" "$ZIM_NAME"
  DOWNLOADED_ZIM="$WIKI_DIR/$ZIM_NAME"
fi

write_settings "$DOWNLOADED_MODEL" "$MODEL_CTX" "$DOWNLOADED_ZIM"

echo ""
echo "Fertig."
echo "Browser:"
echo "  http://127.0.0.1:8787"

if [[ "${MAAT_SETUP_NO_START:-0}" == "1" ]]; then
  echo ""
  echo "Autostart uebersprungen (MAAT_SETUP_NO_START=1)."
  echo "Start:"
  echo "  ./start.sh"
else
  echo ""
  echo "Starte MAAT Web Core jetzt..."
  exec "$ROOT_DIR/start.sh"
fi
