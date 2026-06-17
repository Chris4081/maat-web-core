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

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python3 run.py
