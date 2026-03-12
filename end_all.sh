#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"

OPENCODE_PID_FILE="$RUN_DIR/opencode.pid"

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

pid_running() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

remove_google_sync_cron() {
  local mark_start="# >>> google-workspace-sync (managed) >>>"
  local mark_end="# <<< google-workspace-sync (managed) <<<"

  local existing
  existing="$(crontab -l 2>/dev/null || true)"

  if [[ -z "${existing}" ]]; then
    echo "No crontab entries found."
    return 0
  fi

  local cleaned
  cleaned="$(printf '%s\n' "${existing}" | awk -v s="${mark_start}" -v e="${mark_end}" '
    $0 == s {skip=1; next}
    $0 == e {skip=0; next}
    !skip {print}
  ')"

  if [[ "${cleaned}" == "${existing}" ]]; then
    echo "Managed google-workspace-sync cron block not found."
    return 0
  fi

  if [[ -n "${cleaned}" ]]; then
    printf '%s\n' "${cleaned}" | crontab -
  else
    crontab -r 2>/dev/null || true
  fi

  echo "Removed managed cron: google-workspace-sync."
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
    kill -TERM "$pid" 2>/dev/null || true

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
if need_cmd crontab; then
  remove_google_sync_cron
else
  echo "crontab command not found; skipping managed cron removal."
fi

echo "Done."
