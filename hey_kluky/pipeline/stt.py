import io

from openai import OpenAI

from hey_kluky.config import config


def _get_client() -> OpenAI:
    kwargs = {"api_key": config.OPENAI_API_KEY}
    if config.OPENAI_API_BASE:
        kwargs["base_url"] = config.OPENAI_API_BASE
    return OpenAI(**kwargs)


def transcribe(audio_bytes: bytes) -> str:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")

    client = _get_client()
    audio_buffer = io.BytesIO(audio_bytes)
    audio_buffer.name = "audio.wav"

    result = client.audio.transcriptions.create(
        model=config.WHISPER_MODEL,
        file=audio_buffer,
        language=config.WHISPER_LANGUAGE,
    )
    return result.text
