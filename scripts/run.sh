#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v n8n >/dev/null 2>&1; then
  echo "n8n CLI was not found in PATH. Install n8n first or start it separately." >&2
  exit 1
fi

n8n start &
n8n_pid=$!

cleanup() {
  if kill -0 "$n8n_pid" >/dev/null 2>&1; then
    kill "$n8n_pid"
    wait "$n8n_pid" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

exec python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
