#!/usr/bin/env bash
# Local bot runner (polling mode by default).
# Uses your local .env and starts python bot directly.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  if [[ -f ".env" ]]; then
    # shellcheck disable=SC1091
    source ".env"
  fi
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "[start_bot_local] ERROR: TELEGRAM_BOT_TOKEN is not set."
  echo "Add TELEGRAM_BOT_TOKEN in .env or export it before running."
  exit 1
fi

echo "[start_bot_local] Starting local bot (polling unless WEBHOOK_URL is set)..."
exec python3 -m bot.bot
