#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"

LAUNCHER_PID_FILE="$RUN_DIR/launcher.pid"
SERVER_PID_FILE="$RUN_DIR/server.pid"
OPENCODE_PID_FILE="$RUN_DIR/opencode.pid"
KOKORO_COMPOSE_META_FILE="$RUN_DIR/kokoro.compose"

stop_pid_from_file() {
  local pid_file="$1"
  local label="$2"

  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi

  local pid
  pid="$(tr -d '[:space:]' < "$pid_file" || true)"

  if [[ -z "$pid" ]]; then
    rm -f "$pid_file"
    return 0
  fi

  if kill -0 "$pid" 2>/dev/null; then
    echo "Stopping $label (pid $pid)..."
    kill "$pid" 2>/dev/null || true

    for _ in {1..30}; do
      if ! kill -0 "$pid" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done

    if kill -0 "$pid" 2>/dev/null; then
      echo "Force stopping $label (pid $pid)..."
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi

  rm -f "$pid_file"
}

echo "Stopping hey-kluky services..."

stop_pid_from_file "$LAUNCHER_PID_FILE" "launcher"

# Fallbacks in case launcher is already gone or cleanup did not complete.
stop_pid_from_file "$SERVER_PID_FILE" "Python API server"
stop_pid_from_file "$OPENCODE_PID_FILE" "OpenCode server"

if [[ -f "$KOKORO_COMPOSE_META_FILE" ]]; then
  compose_file="$(tr -d '[:space:]' < "$KOKORO_COMPOSE_META_FILE" || true)"

  if [[ -n "$compose_file" && -f "$compose_file" ]]; then
    if command -v docker >/dev/null 2>&1; then
      echo "Stopping Kokoro stack..."
      docker compose -f "$compose_file" down || true
    else
      echo "docker not found; cannot stop Kokoro automatically"
    fi
  fi

  rm -f "$KOKORO_COMPOSE_META_FILE"
fi

echo "Done."
