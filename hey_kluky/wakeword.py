import io
import openwakeword
import openwakeword.utils
from openwakeword.model import Model
from openwakeword.vad import VAD
from pvrecorder import PvRecorder
import numpy as np
import httpx
import time
import typer
from pydub import AudioSegment

from hey_kluky.settings import settings

app = typer.Typer()


def trigger_api(audio_bytes: bytes, api_base_url: str, api_timeout: float):
    print(f"\n⚡ Wake word detected! Sending audio to API...")
    try:
        api_url = f"{api_base_url}/trigger"

        response = httpx.post(api_url, content=audio_bytes, timeout=api_timeout)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                if result.get("transcription"):
                    print(f"📝 Transcription: {result['transcription']}")
                if result.get("sdk_result"):
                    print(f"🤖 SDK Result: {result['sdk_result']}")
            elif result.get("error"):
                print(f"❌ API Error: {result['error']}")
            else:
                print("✅ API Request Sent")
        else:
            print(f"❌ API Error: HTTP {response.status_code}")
    except httpx.TimeoutException:
        print(f"❌ API Error: /trigger timed out after {api_timeout:.1f}s")
    except Exception as e:
        print(f"❌ API Error: {e}")


def record_until_silence(
    recorder: PvRecorder, silence_timeout: float, max_duration: float
) -> bytes:
    print(f"🔴 Recording... (Speak now, will stop after {silence_timeout}s of silence)")
    frames = []

    # Initialize VAD for recording
    vad = VAD()

    start_time = time.time()
    last_speech_time = time.time()

    while True:
        pcm = recorder.read()
        frames.extend(pcm)

        # Convert to numpy array for VAD
        audio_data = np.array(pcm, dtype=np.int16)

        # Check for speech using VAD
        # VAD returns a score between 0 and 1
        vad_score = vad.predict(audio_data)

        current_time = time.time()

        # If speech is detected (threshold 0.5 is standard for Silero), update last_speech_time
        if vad_score > 0.4:
            last_speech_time = current_time

        # Stop conditions
        silence_duration = current_time - last_speech_time
        total_duration = current_time - start_time

        if silence_duration > silence_timeout:
            print(f"⏹️  Silence detected ({silence_duration:.1f}s). Stopping.")
            break

        if total_duration > max_duration:
            print(f"⏹️  Max duration reached ({max_duration}s). Stopping.")
            break

    # Convert to bytes
    audio_data = np.array(frames, dtype=np.int16).tobytes()

    # Create AudioSegment and export as WAV
    audio_segment = AudioSegment(
        data=audio_data,
        sample_width=2,
        frame_rate=16000,
        channels=1,
    )

    # Export to WAV format in memory
    wav_buffer = io.BytesIO()
    audio_segment.export(wav_buffer, format="wav")
    wav_bytes = wav_buffer.getvalue()

    print(f"🔊 Recorded {len(frames)} frames ({len(wav_bytes)} bytes)")
    return wav_bytes


@app.command()
def main(
    model_name: str = typer.Option("hey_jarvis", help="The wake word model to use."),
    threshold: float = typer.Option(0.5, help="Confidence threshold (0.0 to 1.0)."),
    silence_timeout: float = typer.Option(
        2.0, help="Seconds of silence to stop recording."
    ),
    max_duration: float = typer.Option(
        60.0, help="Maximum recording duration in seconds."
    ),
    ww_vad_threshold: float = typer.Option(
        0.01,
        help="VAD threshold for wake word detection (0.0 to 1.0). Set > 0 to enable.",
    ),
    noise_suppression: bool = typer.Option(
        False, help="Enable Speex noise suppression (Linux only)."
    ),
    api_base_url: str = typer.Option(
        f"http://localhost:{settings.PORT}",
        "--api-base-url",
        envvar="API_BASE_URL",
        help="Base URL of the local API server (e.g. http://localhost:8000).",
    ),
    api_timeout: float = typer.Option(
        120.0,
        "--api-timeout",
        help="Timeout in seconds for /trigger API call.",
    ),
):
    api_base_url = api_base_url.rstrip("/")

    print("Loading models... (this might take a moment first time)")
    openwakeword.utils.download_models(model_names=[model_name])

    model = Model(
        wakeword_models=[model_name],
        vad_threshold=ww_vad_threshold if ww_vad_threshold > 0 else None,
        enable_speex_noise_suppression=noise_suppression,
    )

    recorder = PvRecorder(device_index=-1, frame_length=1280)
    recorder.start()

    print(f"🎤 Listening for '{model_name}' locally... (Ctrl+C to stop)")
    if ww_vad_threshold > 0:
        print(f"\t(VAD Enabled: threshold={ww_vad_threshold})")
    if noise_suppression:
        print("\t(Noise Suppression Enabled)")

    try:
        while True:
            pcm = recorder.read()
            audio_data = np.array(pcm, dtype=np.int16)
            prediction = model.predict(audio_data)
            for m_name, score in prediction.items():
                if score > threshold:
                    try:
                        httpx.post(f"{api_base_url}/stop-tts", timeout=1)
                    except Exception:
                        pass  # Server might not be running yet
                    audio_bytes = record_until_silence(
                        recorder, silence_timeout, max_duration
                    )
                    trigger_api(audio_bytes, api_base_url, api_timeout)
                    model.reset()
                    print(
                        f"🎤 Listening for '{model_name}' locally... (Ctrl+C to stop)"
                    )

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        recorder.stop()
        recorder.delete()
