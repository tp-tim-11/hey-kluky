import io

from elevenlabs import ElevenLabs

from hey_kluky.config import config


def _get_client() -> ElevenLabs:
    if not config.ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not configured")
    return ElevenLabs(api_key=config.ELEVENLABS_API_KEY)


def transcribe(audio_bytes: bytes) -> str:
    client = _get_client()
    audio_buffer = io.BytesIO(audio_bytes)
    audio_buffer.name = "audio.wav"

    result = client.speech_to_text.convert(
        file=audio_buffer,
        model_id=config.ELEVENLABS_STT_MODEL_ID,
        language_code=config.STT_LANGUAGE,
    )
    return result.text
