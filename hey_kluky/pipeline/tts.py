from elevenlabs.client import ElevenLabs
import sounddevice as sd
import soundfile as sf
from io import BytesIO

from ..config import config


client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)


def speak(text: str):
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


def stop():
    sd.stop()
