from elevenlabs.client import ElevenLabs
import sounddevice as sd
import soundfile as sf
from io import BytesIO

from ..config import config

_client: ElevenLabs | None = None


def _get_client() -> ElevenLabs:
    global _client
    api_key = config.ELEVENLABS_API_KEY.strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured")
    if _client is None:
        _client = ElevenLabs(api_key=api_key)
    return _client


def speak(text: str):
    client = _get_client()
    try:
        audio_generator = client.text_to_speech.convert(
            text=text,
            voice_id=config.ELEVENLABS_VOICE_ID,
            model_id=config.ELEVENLABS_MODEL_ID,
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_generator)
        samples, samplerate = sf.read(BytesIO(audio_bytes))
        sd.play(samples, samplerate=samplerate)
        sd.wait()
    except Exception as e:
        raise RuntimeError(f"TTS playback failed: {e}") from e


def stop():
    sd.stop()
