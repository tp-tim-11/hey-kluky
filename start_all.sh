#!/usr/bin/env bash
set -euo pipefail

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 1
  }
}

is_listening() {
  local host="$1"
  local port="$2"
  nc -z "$host" "${port}" 2>/dev/null
}

wait_for_port() {
  local host="$1"
  local port="$2"
  local timeout="${3:-45}"
  local i
  for ((i=0; i<timeout; i++)); do
    if is_listening "$host" "$port"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

pid_running() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

install_google_sync_cron() {
  local project_dir="${GOOGLE_WORKSPACE_SYNC_DIR}"
  local log_dir="${project_dir}/logs"
  local lock_dir="/tmp/gws_all.lck"
  local mark_start="# >>> google-workspace-sync (managed) >>>"
  local mark_end="# <<< google-workspace-sync (managed) <<<"

  if [[ ! -d "${project_dir}" ]]; then
    echo "ERROR: GOOGLE_WORKSPACE_SYNC_DIR does not exist: ${project_dir}"
    return 1
  fi

  mkdir -p "${log_dir}"

  local uv_bin
  local bash_bin
  uv_bin="$(command -v uv)"
  bash_bin="$(command -v bash)"

  local inner
  inner="cd \"${project_dir}\" && \"${uv_bin}\" run google-workspace-sync sync --mode all >> \"${log_dir}/all-sync.log\" 2>&1"

  # Use atomic mkdir as a cross-platform lock (works on Linux and macOS)
  local locked_inner
  locked_inner="mkdir ${lock_dir} 2>/dev/null || exit 0; trap \"rmdir ${lock_dir}\" EXIT; ${inner}"

  local cron_line
  cron_line="*/5 * * * * ${bash_bin} -lc '${locked_inner}'"

  local managed_block
  managed_block="${mark_start}
# Managed by hey-kluky/start_all.sh
${cron_line}
${mark_end}"

  local existing
  existing="$(crontab -l 2>/dev/null || true)"

  local cleaned
  cleaned="$(printf '%s\n' "${existing}" | awk -v s="${mark_start}" -v e="${mark_end}" '
    $0 == s {skip=1; next}
    $0 == e {skip=0; next}
    !skip {print}
  ')"

  local new_crontab
  if [[ -n "${cleaned}" ]]; then
    new_crontab="${cleaned}
${managed_block}
"
  else
    new_crontab="${managed_block}
"
  fi

  printf '%s' "${new_crontab}" | crontab -
  echo "Installed managed cron: google-workspace-sync sync --mode all every 5 minutes."
}

load_settings() {
  uv run python - <<'PY'
from pathlib import Path
from urllib.parse import urlparse

from hey_kluky.config import config

test_dir_raw = (config.TEST_OPENCODE_DIR or "").strip()
if not test_dir_raw:
    raise SystemExit("ERROR: TEST_OPENCODE_DIR is empty. Set it in ../.env.")

test_dir = Path(test_dir_raw).expanduser()
if not test_dir.is_absolute():
    test_dir = (Path.cwd() / test_dir).resolve()
else:
    test_dir = test_dir.resolve()

if not test_dir.is_dir():
    raise SystemExit(f"ERROR: TEST_OPENCODE_DIR does not exist: {test_dir}")

opencode_url = (config.OPENCODE_URL or "").strip()
parsed = urlparse(opencode_url)

if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.port is None:
    raise SystemExit("ERROR: OPENCODE_URL must include scheme, host, and port (e.g. http://127.0.0.1:4096)")

gws_dir_raw = (config.GOOGLE_WORKSPACE_SYNC_DIR or "").strip()
if not gws_dir_raw:
    raise SystemExit("ERROR: GOOGLE_WORKSPACE_SYNC_DIR is empty. Set it in ../.env.")

gws_dir = Path(gws_dir_raw).expanduser().resolve()

print(f"TEST_OPENCODE_DIR={test_dir}")
print(f"OPENCODE_URL={opencode_url}")
print(f"OPENCODE_HOST={parsed.hostname}")
print(f"OPENCODE_PORT={parsed.port}")
print(f"GOOGLE_WORKSPACE_SYNC_DIR={gws_dir}")
PY
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"
mkdir -p "$RUN_DIR"

OPENCODE_PID_FILE="$RUN_DIR/opencode.pid"
OPENCODE_LOG_FILE="$RUN_DIR/opencode.log"
SHEET_PUSH_PID_FILE="$RUN_DIR/sheet_push_watch.pid"
SHEET_PUSH_LOG_FILE="$RUN_DIR/sheet_push_watch.log"

if [[ $# -gt 0 ]]; then
  echo "start_all.sh does not accept options. Configure ../.env instead."
  echo "Expected settings: TEST_OPENCODE_DIR, OPENCODE_URL, API_HOST, API_PORT, WAKEWORD_MODEL_NAME, GOOGLE_WORKSPACE_SYNC_DIR"
  exit 1
fi

need_cmd uv
need_cmd opencode
need_cmd nc
need_cmd crontab

settings_output="$(
  cd "$ROOT"
  load_settings
)"

while IFS='=' read -r key value; do
  case "$key" in
    TEST_OPENCODE_DIR) TEST_OPENCODE_DIR="$value" ;;
    OPENCODE_URL) OPENCODE_URL="$value" ;;
    OPENCODE_HOST) OPENCODE_HOST="$value" ;;
    OPENCODE_PORT) OPENCODE_PORT="$value" ;;
    GOOGLE_WORKSPACE_SYNC_DIR) GOOGLE_WORKSPACE_SYNC_DIR="$value" ;;
  esac
done <<< "$settings_output"

if [[ -z "${TEST_OPENCODE_DIR:-}" || -z "${OPENCODE_URL:-}" || -z "${OPENCODE_HOST:-}" || -z "${OPENCODE_PORT:-}" || -z "${GOOGLE_WORKSPACE_SYNC_DIR:-}" ]]; then
  echo "Failed to load required settings from ../.env"
  exit 1
fi

install_google_sync_cron

OPENCODE_STARTED=0
OPENCODE_PID=""
SHEET_PUSH_STARTED=0
SHEET_PUSH_PID=""

ensure_sheet_push_watch() {
  echo "Ensuring Google Sheet push watcher (DB -> Sheet)"

  if [[ -f "$SHEET_PUSH_PID_FILE" ]]; then
    local existing_pid
    existing_pid="$(tr -d '[:space:]' < "$SHEET_PUSH_PID_FILE" || true)"
    if [[ -n "$existing_pid" ]] && pid_running "$existing_pid"; then
      SHEET_PUSH_PID="$existing_pid"
      echo "Sheet push watcher already running (pid $SHEET_PUSH_PID), reusing."
      return 0
    fi
    rm -f "$SHEET_PUSH_PID_FILE"
    echo "Removed stale Sheet push watcher PID file."
  fi

  (
    cd "$GOOGLE_WORKSPACE_SYNC_DIR"
    exec uv run google-workspace-sync watch-sheet-push \
      > "$SHEET_PUSH_LOG_FILE" 2>&1
  ) &
  SHEET_PUSH_PID="$!"
  echo "$SHEET_PUSH_PID" > "$SHEET_PUSH_PID_FILE"
  SHEET_PUSH_STARTED=1

  sleep 1
  if ! pid_running "$SHEET_PUSH_PID"; then
    echo "WARNING: Sheet push watcher exited during startup."
    echo "See logs: $SHEET_PUSH_LOG_FILE"
    rm -f "$SHEET_PUSH_PID_FILE"
    SHEET_PUSH_STARTED=0
    SHEET_PUSH_PID=""
    return 0
  fi

  echo "Sheet push watcher started (pid $SHEET_PUSH_PID)."
  echo "Watcher logs: $SHEET_PUSH_LOG_FILE"
}

cleanup() {
  set +e
  if [[ "$OPENCODE_STARTED" -eq 1 && -n "$OPENCODE_PID" ]] && pid_running "$OPENCODE_PID"; then
    echo
    echo "Stopping OpenCode server (pid $OPENCODE_PID)..."
    kill -TERM "$OPENCODE_PID" 2>/dev/null || true
    for _ in {1..30}; do
      if ! pid_running "$OPENCODE_PID"; then
        break
      fi
      sleep 0.2
    done
    if pid_running "$OPENCODE_PID"; then
      kill -9 "$OPENCODE_PID" 2>/dev/null || true
    fi
  fi
  if [[ "$OPENCODE_STARTED" -eq 1 ]]; then
    rm -f "$OPENCODE_PID_FILE"
  fi

  if [[ "$SHEET_PUSH_STARTED" -eq 1 && -n "$SHEET_PUSH_PID" ]] && pid_running "$SHEET_PUSH_PID"; then
    echo
    echo "Stopping Sheet push watcher (pid $SHEET_PUSH_PID)..."
    kill -TERM "$SHEET_PUSH_PID" 2>/dev/null || true
    for _ in {1..30}; do
      if ! pid_running "$SHEET_PUSH_PID"; then
        break
      fi
      sleep 0.2
    done
    if pid_running "$SHEET_PUSH_PID"; then
      kill -9 "$SHEET_PUSH_PID" 2>/dev/null || true
    fi
  fi
  if [[ "$SHEET_PUSH_STARTED" -eq 1 ]]; then
    rm -f "$SHEET_PUSH_PID_FILE"
  fi
}
trap cleanup EXIT INT TERM

ensure_sheet_push_watch

echo "Ensuring OpenCode server on ${OPENCODE_HOST}:${OPENCODE_PORT}"
if is_listening "$OPENCODE_HOST" "$OPENCODE_PORT"; then
  echo "OpenCode already listening on $OPENCODE_PORT, reusing."
  if [[ -f "$OPENCODE_PID_FILE" ]]; then
    existing_pid="$(tr -d '[:space:]' < "$OPENCODE_PID_FILE" || true)"
    if [[ -z "$existing_pid" ]] || ! pid_running "$existing_pid"; then
      rm -f "$OPENCODE_PID_FILE"
      echo "Removed stale OpenCode PID file."
    fi
  fi
else
  (
    cd "$TEST_OPENCODE_DIR"
    exec opencode serve --hostname "$OPENCODE_HOST" --port "$OPENCODE_PORT" --print-logs \
      > "$OPENCODE_LOG_FILE" 2>&1
  ) &
  OPENCODE_PID="$!"
  echo "$OPENCODE_PID" > "$OPENCODE_PID_FILE"
  OPENCODE_STARTED=1

  wait_for_port "$OPENCODE_HOST" "$OPENCODE_PORT" 45 || {
    echo "OpenCode failed to open port $OPENCODE_PORT"
    echo "See logs: $OPENCODE_LOG_FILE"
    exit 1
  }
fi

echo "Starting main.py in foreground..."
echo "Using TEST_OPENCODE_DIR=$TEST_OPENCODE_DIR"
echo "Using OPENCODE_URL=$OPENCODE_URL"
echo "Press Ctrl+C to stop."

cd "$ROOT"
export TEST_OPENCODE_DIR
export OPENCODE_URL
uv run python main.py
