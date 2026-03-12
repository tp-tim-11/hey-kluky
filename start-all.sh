#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./start-all.sh --test-dir <path> [options] [-- <wakeword args>]

Starts (in order):
  1) Kokoro TTS (Docker compose)
  2) OpenCode server
  3) Python API server (server.py)
  4) Wakeword listener (main.py, foreground)

Note:
  OPENAI_API_KEY is required by server.py and is read via hey_kluky/settings.py
  from shell environment or .env.

Options:
  --test-dir PATH           Directory sent to OpenCode SDK (required)
  --opencode-dir PATH       Directory where `opencode serve` is started
                            (default: same as --test-dir)
  --server-port N           Python API port (default: 8000)
  --opencode-port N         OpenCode server port (default: 4096)
  --kokoro cpu|gpu|skip     Kokoro startup mode (default: cpu)
  --skip-install            Skip `uv sync` and `npm ci`
  --keep-kokoro             Do not stop Kokoro on exit
  -h, --help                Show this help

Examples:
  ./start-all.sh --test-dir /abs/path/to/project
  ./start-all.sh --test-dir /abs/path --server-port 8010
  ./start-all.sh --test-dir /abs/path -- --model-name hey_jarvis --threshold 0.55
EOF
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 1
  }
}

is_listening() {
  local port="$1"
  ss -ltn | grep -q ":${port} "
}

wait_for_port() {
  local port="$1"
  local timeout="${2:-30}"
  local i
  for ((i=0; i<timeout; i++)); do
    if is_listening "$port"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_http() {
  local url="$1"
  local timeout="${2:-60}"
  local i
  for ((i=0; i<timeout; i++)); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT/.run"
mkdir -p "$RUN_DIR"

LAUNCHER_PID_FILE="$RUN_DIR/launcher.pid"
SERVER_PID_FILE="$RUN_DIR/server.pid"
OPENCODE_PID_FILE="$RUN_DIR/opencode.pid"
KOKORO_COMPOSE_META_FILE="$RUN_DIR/kokoro.compose"

rm -f "$LAUNCHER_PID_FILE" "$SERVER_PID_FILE" "$OPENCODE_PID_FILE"
echo "$$" > "$LAUNCHER_PID_FILE"

TEST_DIR=""
OPENCODE_DIR=""
SERVER_HOST="127.0.0.1"
SERVER_PORT="8000"
OPENCODE_HOST="127.0.0.1"
OPENCODE_PORT="4096"
KOKORO_MODE="cpu"
SKIP_INSTALL=0
KEEP_KOKORO=0
WAKEWORD_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --test-dir) TEST_DIR="$2"; shift 2 ;;
    --opencode-dir) OPENCODE_DIR="$2"; shift 2 ;;
    --server-port) SERVER_PORT="$2"; shift 2 ;;
    --opencode-port) OPENCODE_PORT="$2"; shift 2 ;;
    --kokoro) KOKORO_MODE="$2"; shift 2 ;;
    --skip-install) SKIP_INSTALL=1; shift ;;
    --keep-kokoro) KEEP_KOKORO=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; WAKEWORD_ARGS=("$@"); break ;;
    *) echo "Unknown option: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "$TEST_DIR" ]]; then
  echo "Missing required option: --test-dir"
  usage
  exit 1
fi

if [[ -z "$OPENCODE_DIR" ]]; then
  OPENCODE_DIR="$TEST_DIR"
fi

if [[ ! -d "$ROOT/opencode-sdk" ]]; then
  echo "Missing directory: $ROOT/opencode-sdk"
  exit 1
fi

if [[ ! -d "$ROOT/Kokoro-FastAPI" && "$KOKORO_MODE" != "skip" ]]; then
  echo "Missing directory: $ROOT/Kokoro-FastAPI"
  exit 1
fi

if [[ ! -d "$TEST_DIR" ]]; then
  echo "--test-dir does not exist: $TEST_DIR"
  exit 1
fi

if [[ ! -d "$OPENCODE_DIR" ]]; then
  echo "--opencode-dir does not exist: $OPENCODE_DIR"
  exit 1
fi

need_cmd uv
need_cmd node
need_cmd npm
need_cmd opencode
need_cmd curl
need_cmd ss
if [[ "$KOKORO_MODE" != "skip" ]]; then
  need_cmd docker
fi

if is_listening "$SERVER_PORT"; then
  echo "Server port $SERVER_PORT is already in use. Pick another with --server-port."
  exit 1
fi

OPENCODE_PID=""
SERVER_PID=""
KOKORO_STARTED=0
KOKORO_COMPOSE_FILE=""

cleanup() {
  set +e
  if [[ -n "$SERVER_PID" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
  fi
  if [[ -n "$OPENCODE_PID" ]] && kill -0 "$OPENCODE_PID" 2>/dev/null; then
    kill "$OPENCODE_PID" 2>/dev/null || true
  fi
  if [[ "$KOKORO_STARTED" -eq 1 && "$KEEP_KOKORO" -eq 0 ]]; then
    docker compose -f "$KOKORO_COMPOSE_FILE" down || true
    rm -f "$KOKORO_COMPOSE_META_FILE"
  fi

  rm -f "$SERVER_PID_FILE" "$OPENCODE_PID_FILE" "$LAUNCHER_PID_FILE"
}
trap cleanup EXIT INT TERM

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  echo "[1/6] Installing Python dependencies (uv sync)..."
  (cd "$ROOT" && uv sync)

  echo "[2/6] Installing Node dependencies (opencode-sdk)..."
  npm ci --prefix "$ROOT/opencode-sdk"
else
  echo "[1/6] Skipping dependency install (--skip-install)."
fi

echo "[3/6] Starting Kokoro mode: $KOKORO_MODE"
case "$KOKORO_MODE" in
  cpu)
    if is_listening 8880; then
      echo "Kokoro already listening on 8880, reusing."
    else
      KOKORO_COMPOSE_FILE="$ROOT/Kokoro-FastAPI/docker/cpu/docker-compose.yml"
      (
        cd "$ROOT/Kokoro-FastAPI/docker/cpu"
        docker compose up -d --build
      )
      KOKORO_STARTED=1
      echo "$KOKORO_COMPOSE_FILE" > "$KOKORO_COMPOSE_META_FILE"
      wait_for_port 8880 180 || {
        echo "Kokoro did not open port 8880 in time"
        exit 1
      }
    fi
    ;;
  gpu)
    if is_listening 8880; then
      echo "Kokoro already listening on 8880, reusing."
    else
      KOKORO_COMPOSE_FILE="$ROOT/Kokoro-FastAPI/docker/gpu/docker-compose.yml"
      (
        cd "$ROOT/Kokoro-FastAPI/docker/gpu"
        docker compose up -d --build
      )
      KOKORO_STARTED=1
      echo "$KOKORO_COMPOSE_FILE" > "$KOKORO_COMPOSE_META_FILE"
      wait_for_port 8880 180 || {
        echo "Kokoro did not open port 8880 in time"
        exit 1
      }
    fi
    ;;
  skip)
    if ! is_listening 8880; then
      echo "Warning: Kokoro not started and nothing on 8880. TTS will fail."
    fi
    ;;
  *)
    echo "Invalid --kokoro value: $KOKORO_MODE (use cpu|gpu|skip)"
    exit 1
    ;;
esac

echo "[4/6] Starting OpenCode server on ${OPENCODE_HOST}:${OPENCODE_PORT}"
if is_listening "$OPENCODE_PORT"; then
  echo "Something already listens on $OPENCODE_PORT, reusing."
else
  (
    cd "$OPENCODE_DIR"
    opencode serve --hostname "$OPENCODE_HOST" --port "$OPENCODE_PORT" --print-logs \
      > "$RUN_DIR/opencode.log" 2>&1
  ) &
  OPENCODE_PID="$!"
  echo "$OPENCODE_PID" > "$OPENCODE_PID_FILE"
  wait_for_port "$OPENCODE_PORT" 45 || {
    echo "OpenCode server did not open port $OPENCODE_PORT"
    exit 1
  }
fi

echo "[5/6] Starting Python API on ${SERVER_HOST}:${SERVER_PORT}"
(
  cd "$ROOT"
  export HOST="$SERVER_HOST"
  export PORT="$SERVER_PORT"
  export TEST_OPENCODE_DIR="$TEST_DIR"
  export OPENCODE_URL="http://${OPENCODE_HOST}:${OPENCODE_PORT}"

  uv run python server.py > "$RUN_DIR/server.log" 2>&1
) &
SERVER_PID="$!"
echo "$SERVER_PID" > "$SERVER_PID_FILE"

wait_for_http "http://${SERVER_HOST}:${SERVER_PORT}/health" 60 || {
  echo "Python API failed to become healthy"
  echo "See logs: $RUN_DIR/server.log"
  exit 1
}

echo "[6/6] Starting wakeword listener (foreground)"
echo "Logs:"
echo "  API:      $RUN_DIR/server.log"
echo "  OpenCode: $RUN_DIR/opencode.log"

(
  cd "$ROOT"
  export API_BASE_URL="http://${SERVER_HOST}:${SERVER_PORT}"
  uv run python main.py --api-base-url "$API_BASE_URL" "${WAKEWORD_ARGS[@]}"
)
