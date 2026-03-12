# hey-kluky

`hey-kluky` is a wake-word voice assistant loop:

1. wait for wake word
2. record audio
3. transcribe with OpenAI Whisper
4. send text to an OpenCode server session

The app entrypoint is `main.py`.

## Current prerequisites

- `uv`
- `opencode` CLI
- Linux audio dependencies for `sounddevice`/microphone access
- Python `3.11` (important: `tflite-runtime` used by `openwakeword` does not currently install on `3.13`)

## Environment

Copy `.env-example` to `.env`:

```bash
cp .env-example .env
```

Required:

- `OPENAI_API_KEY`
- `TEST_OPENCODE_DIR` (directory OpenCode should use for context/execution)

Common optional values:

- `OPENAI_API_BASE`
- `OPENCODE_URL` (default: `http://localhost:4096`)
- `OPENCODE_PROVIDER_ID` and `OPENCODE_MODEL_ID`
- `API_HOST`, `API_PORT`
- `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL_ID`

## One-time model download (openwakeword assets)

If you see missing model files such as `silero_vad.onnx`, run:

```bash
uv run python -c "import openwakeword.utils as u; u.download_models()"
```

## Start everything with scripts

This repo now provides `start_all.sh` and `end_all.sh`.

```bash
chmod +x start_all.sh end_all.sh
./start_all.sh
```

`start_all.sh` does:

1. loads settings from `.env` through `hey_kluky/config.py` (pydantic-settings)
2. validates `TEST_OPENCODE_DIR`
3. installs managed cron for `google-workspace-sync sync --mode all` every 5 minutes
4. starts `opencode serve` (or reuses existing server on `OPENCODE_URL` port)
5. runs `uv run python main.py` in foreground (live logs in your terminal)

Logs:

- `.run/opencode.log`

`start_all.sh` does not accept CLI options. Configure `.env` instead.

Stop managed OpenCode process from PID file:

```bash
./end_all.sh
```

`end_all.sh` also removes the managed `google-workspace-sync` cron block.

## Manual run (without helper scripts)

Terminal 1 (in target project directory):

```bash
opencode serve --hostname 127.0.0.1 --port 4096
```

Terminal 2 (this repo):

```bash
TEST_OPENCODE_DIR=/absolute/path/to/target/project uv run main.py
```

If OpenCode runs elsewhere:

```bash
OPENCODE_URL=http://127.0.0.1:4097 TEST_OPENCODE_DIR=/absolute/path uv run main.py
```

## CLI options

Show all options:

```bash
uv run python main.py --help
```

Common options:

- `--text`: run one text request (skip wakeword + recording)
- `--threshold`: wakeword confidence threshold
- `--silence-timeout`: stop recording after silence seconds
- `--max-duration`: cap recording duration
- `--ww-vad-threshold`: wakeword VAD threshold (`0` disables VAD)
- `--api-host`, `--api-port`: internal FastAPI server used by the app

## Troubleshooting

- `OpenCode Error: [Errno 111] Connection refused`
  - OpenCode server is not running at `OPENCODE_URL`.
- `ERROR: TEST_OPENCODE_DIR does not exist`
  - Set `TEST_OPENCODE_DIR` in `.env` to a valid existing directory.
- `NoSuchFile ... silero_vad.onnx`
  - Run the one-time model download command above.
- `tflite-runtime ... cp313`
  - Recreate the environment with Python `3.11`.
