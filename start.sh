#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Passwortschutz fuer MAAT Web Core.
# Beim Start kannst du ihn aktivieren oder ohne Passwort lokal starten.
DEFAULT_AUTH_USER="${MAAT_WEB_AUTH_USER:-admin}"
DEFAULT_AUTH_PASSWORD="${MAAT_WEB_AUTH_PASSWORD:-maat}"

lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

echo ""
echo "MAAT Web Core Passwortschutz"
read -r -p "Passwortschutz aktivieren? [J/n]: " AUTH_CHOICE
AUTH_CHOICE="$(lower "$AUTH_CHOICE")"

if [[ "$AUTH_CHOICE" == "n" || "$AUTH_CHOICE" == "nein" || "$AUTH_CHOICE" == "no" || "$AUTH_CHOICE" == "0" ]]; then
  export MAAT_WEB_AUTH_ENABLED="0"
  unset MAAT_WEB_AUTH_USER
  unset MAAT_WEB_AUTH_PASSWORD
  echo "Passwortschutz aus."
else
  read -r -p "Benutzer [$DEFAULT_AUTH_USER]: " AUTH_USER
  AUTH_USER="${AUTH_USER:-$DEFAULT_AUTH_USER}"

  read -r -s -p "Passwort [Enter = Standard]: " AUTH_PASSWORD
  echo ""
  AUTH_PASSWORD="${AUTH_PASSWORD:-$DEFAULT_AUTH_PASSWORD}"

  export MAAT_WEB_AUTH_ENABLED="1"
  export MAAT_WEB_AUTH_USER="$AUTH_USER"
  export MAAT_WEB_AUTH_PASSWORD="$AUTH_PASSWORD"
  echo "Passwortschutz an fuer Benutzer: $MAAT_WEB_AUTH_USER"
fi

echo ""
echo "MAAT Web Core Netzwerk"
DEFAULT_PORT="${MAAT_WEB_PORT:-8787}"
read -r -p "Im LAN/iPad/Handy erreichbar machen? [j/N]: " LAN_CHOICE
LAN_CHOICE="$(lower "$LAN_CHOICE")"
read -r -p "Port [$DEFAULT_PORT]: " WEB_PORT
WEB_PORT="${WEB_PORT:-$DEFAULT_PORT}"
export MAAT_WEB_PORT="$WEB_PORT"

if [[ "$LAN_CHOICE" == "j" || "$LAN_CHOICE" == "ja" || "$LAN_CHOICE" == "y" || "$LAN_CHOICE" == "yes" || "$LAN_CHOICE" == "1" ]]; then
  export MAAT_WEB_HOST="0.0.0.0"
  LAN_IP=""
  if command -v ipconfig >/dev/null 2>&1; then
    LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
    if [[ -z "$LAN_IP" ]]; then
      LAN_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
    fi
  fi
  if [[ -z "$LAN_IP" ]] && command -v hostname >/dev/null 2>&1; then
    LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  fi
  echo "LAN-Zugriff an."
  if [[ -n "$LAN_IP" ]]; then
    echo "Im Browser eines Geräts im selben Netzwerk öffnen: http://$LAN_IP:$MAAT_WEB_PORT"
  else
    echo "IP konnte nicht automatisch gelesen werden. Nutze die lokale LAN-IP dieses Rechners."
  fi
else
  export MAAT_WEB_HOST="127.0.0.1"
  echo "Nur lokal erreichbar: http://127.0.0.1:$MAAT_WEB_PORT"
fi

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python3 run.py
