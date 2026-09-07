#!/usr/bin/env bash
# Runs backend (FastAPI/uvicorn) and frontend (Vite) together, tearing both down on Ctrl+C.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "Backend virtualenv not found at $BACKEND_DIR/.venv — see README.md to set it up first." >&2
  exit 1
fi

PIDS=()
cleanup() {
  echo ""
  echo "Stopping..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(
  cd "$BACKEND_DIR"
  source .venv/bin/activate
  exec uvicorn app.main:app --reload --port "$BACKEND_PORT"
) &
PIDS+=($!)

(
  cd "$FRONTEND_DIR"
  exec npm run dev -- --port "$FRONTEND_PORT"
) &
PIDS+=($!)

echo "Backend  → http://localhost:$BACKEND_PORT"
echo "Frontend → http://localhost:$FRONTEND_PORT"
echo "Press Ctrl+C to stop both."

wait
