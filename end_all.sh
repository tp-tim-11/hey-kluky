#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"

OPENCODE_PID_FILE="$RUN_DIR/opencode.pid"

pid_running() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

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

  if pid_running "$pid"; then
    echo "Stopping $label (pid $pid)..."
    kill "$pid" 2>/dev/null || true

    for _ in {1..30}; do
      if ! pid_running "$pid"; then
        break
      fi
      sleep 0.2
    done

    if pid_running "$pid"; then
      echo "Force stopping $label (pid $pid)..."
      kill -9 "$pid" 2>/dev/null || true
    fi
  else
    echo "$label pid file exists, but process is already stopped."
  fi

  rm -f "$pid_file"
}

echo "Stopping hey-kluky managed processes..."

stop_pid_from_file "$OPENCODE_PID_FILE" "OpenCode server"

echo "Done."
