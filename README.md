# hey-kluky

`hey-kluky` is a wake word detection tool powered by [OpenWakeWord](https://github.com/dscripka/openWakeWord). It listens for a specific wake word (default: "hey_jarvis") and triggers an API endpoint when detected.

## Usage

You can run the CLI tool using Python. Ensure you have the dependencies installed.

### Custom Configuration
You can customize the behavior using command-line options:

- **--model-name**: The wake word model to use (e.g., `alexa`, `hey_mycroft`, `hey_jarvis`).
- **--threshold**: The confidence threshold (0.0 to 1.0). Higher values reduce false positives but might miss some detections.
- **--silence-timeout**: Seconds of silence to stop recording (default: 1.0).
- **--max-duration**: Maximum recording duration in seconds (default: 30.0).
- **--ww-vad-threshold**: VAD threshold for wake word detection (0.0 to 1.0). Set > 0 to enable.
- **--noise-suppression**: Enable Speex noise suppression (Linux only).

#### Examples

```bash
python main.py --model-name=hey_jarvis --threshold=0.5 --silence-timeout=1.0 --max-duration=30.0 --ww-vad-threshold=0.01 --noise-suppression=False
```

```bash
python main.py --help
```