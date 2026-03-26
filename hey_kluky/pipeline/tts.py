from pathlib import Path

from elevenlabs.client import ElevenLabs
import sounddevice as sd
import soundfile as sf
from io import BytesIO

from ..config import config

_client: ElevenLabs | None = None

_SOUNDS_DIR = Path(__file__).resolve().parent.parent / "sounds"
_CACHE_DIR = _SOUNDS_DIR / "tts_cache"
_LAST_CACHE_PATH = _CACHE_DIR / "last.mp3"
_WAIT_MUSIC_DIR = _SOUNDS_DIR / "tts_wait_music"
_CONFIRMATION_PATH = _SOUNDS_DIR / "confirmation.mp3"

_last_audio_bytes: bytes | None = None


def _get_client() -> ElevenLabs:
    global _client
    api_key = config.ELEVENLABS_API_KEY.strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not configured")
    if _client is None:
        _client = ElevenLabs(api_key=api_key)
    return _client


def speak(text: str):
    global _last_audio_bytes
    from .timer import timer

    try:
        timer.start("TTS Generation")
        client = _get_client()
        audio_generator = client.text_to_speech.convert(
            text=text,
            voice_id=config.ELEVENLABS_VOICE_ID,
            model_id=config.ELEVENLABS_MODEL_ID,
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_generator)

        # Cache the TTS audio
        _last_audio_bytes = audio_bytes
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _LAST_CACHE_PATH.write_bytes(audio_bytes)

        timer.start("TTS Playback")
        samples, samplerate = sf.read(BytesIO(audio_bytes))
        sd.play(samples, samplerate=samplerate)
        sd.wait()
        timer.stop()
    except Exception as e:
        timer.stop()
        raise RuntimeError(f"TTS playback failed: {e}") from e


def play_wait_music():
    """Play na_bicykle.mp3 first, then a random mp3 from the wait music folder (non-blocking) while LLM is thinking."""
    import random

    try:
        # Play na_bicykle.mp3 before wait music
        na_bicykle_path = _SOUNDS_DIR / "na_bicykle.mp3"
        if na_bicykle_path.exists():
            samples, samplerate = sf.read(str(na_bicykle_path))
            sd.play(samples, samplerate=samplerate)
            sd.wait()
        else:
            print("na_bicykle.mp3 not found in sounds", flush=True)

        files = list(_WAIT_MUSIC_DIR.glob("*.mp3"))
        if not files:
            print("No wait music files found", flush=True)
            return
        path = random.choice(files)
        samples, samplerate = sf.read(str(path))
        sd.play(samples, samplerate=samplerate)
    except Exception as e:
        print(f"Could not play wait music: {e}", flush=True)


def play_confirmation():
    """Play the confirmation sound after wakeword detection (blocking)."""
    try:
        if not _CONFIRMATION_PATH.exists():
            print("No confirmation sound found", flush=True)
            return
        samples, samplerate = sf.read(str(_CONFIRMATION_PATH))
        sd.play(samples, samplerate=samplerate)
        sd.wait()
    except Exception as e:
        print(f"Could not play confirmation sound: {e}", flush=True)


def play_cached():
    """Play the last cached TTS audio from disk."""
    if not _LAST_CACHE_PATH.exists():
        raise RuntimeError("No cached TTS audio found")
    samples, samplerate = sf.read(str(_LAST_CACHE_PATH))
    sd.play(samples, samplerate=samplerate)
    sd.wait()


def stop():
    sd.stop()
