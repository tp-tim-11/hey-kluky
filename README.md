# hey-kluky

`hey-kluky` is a wake word detection tool powered by [OpenWakeWord](https://github.com/dscripka/openWakeWord). It listens for a specific wake word (default: "hey_jarvis") and triggers an API endpoint when detected.

## Prerequisites

- `uv`
- `node` + `npm`
- `opencode` CLI
- `docker` (for Kokoro TTS)

## Environment

Copy `.env-example` to `.env` and fill the required values:

```bash
cp .env-example .env
```

`server.py` reads `.env` through `hey_kluky/settings.py`.

Required:

- `OPENAI_API_KEY`

Optional (depending on setup):

- `OPENAI_API_BASE`
- `ANTHROPIC_API_KEY` (if set, Anthropic intent classifier is used; if empty, local keyword classifier is used)
- `OPENCODE_PROVIDER_ID` and `OPENCODE_MODEL_ID` (defaults: `github-copilot` / `gpt-4.1`)

## Run the full app

Use `start-all.sh` to launch all dependencies in order:

1. Kokoro TTS (Docker)
2. OpenCode server
3. Python API server (`server.py`)
4. Wakeword listener (`main.py`)

```bash
chmod +x start-all.sh
./start-all.sh --test-dir /absolute/path/to/target/project
```

If you want to override `.env` for one run, pass vars inline:

```bash
OPENAI_API_KEY=... ./start-all.sh --test-dir /absolute/path/to/target/project
```

Common options:

- `--test-dir PATH`: directory sent to OpenCode SDK as working context (required)
- `--opencode-dir PATH`: directory where `opencode serve` is started (default: same as `--test-dir`)
- `--server-port N`: Python API port (default: `8000`)
- `--opencode-port N`: OpenCode server port (default: `4096`)
- `--kokoro cpu|gpu|skip`: start CPU, GPU, or skip Kokoro startup
- `--skip-install`: skip `uv sync` and `npm ci`

Pass wakeword CLI options after `--`:

```bash
./start-all.sh --test-dir /abs/path -- --model-name hey_jarvis --threshold 0.55
```

Custom API port example:

```bash
./start-all.sh --test-dir /abs/path --server-port 8010
```

`start-all.sh` sets `API_BASE_URL` automatically so wakeword uses the same API port.

Logs are written to `.run/server.log` and `.run/opencode.log`.

Stop everything started by the launcher:

```bash
chmod +x stop-all.sh
./stop-all.sh
```

## Wakeword CLI usage

You can run the CLI tool using Python. Ensure you have the dependencies installed.

### Custom Configuration
You can customize the behavior using command-line options:

- **--model-name**: The wake word model to use (e.g., `alexa`, `hey_mycroft`, `hey_jarvis`).
- **--threshold**: The confidence threshold (0.0 to 1.0). Higher values reduce false positives but might miss some detections.
- **--silence-timeout**: Seconds of silence to stop recording (default: 1.0).
- **--max-duration**: Maximum recording duration in seconds (default: 30.0).
- **--ww-vad-threshold**: VAD threshold for wake word detection (0.0 to 1.0). Set > 0 to enable.
- **--noise-suppression**: Enable Speex noise suppression (Linux only).
- **--api-base-url**: Base URL of the local API server that handles `/trigger` and `/stop-tts`.
- **--api-timeout**: Timeout in seconds for the `/trigger` API call (default: 120.0).

You can also set `API_BASE_URL` as an environment variable. By default it uses `http://localhost:<PORT>`, where `PORT` is read from environment (default: `8000`).

#### Examples

```bash
python main.py --model-name=hey_jarvis --threshold=0.5 --silence-timeout=1.0 --max-duration=30.0 --ww-vad-threshold=0.01 --noise-suppression=False
```

```bash
PORT=8010 python server.py
API_BASE_URL=http://localhost:8010 python main.py
```

```bash
python main.py --help
```
