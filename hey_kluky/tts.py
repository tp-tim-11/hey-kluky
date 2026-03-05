from openai import OpenAI
import sounddevice as sd
import numpy as np
import io
import soundfile as sf

client = OpenAI(base_url="http://localhost:8880/v1", api_key="not-needed")

def speak(text: str):
    with client.audio.speech.with_streaming_response.create(
        model="kokoro",
        voice="af_sky+af_bella",
        input=text,
        response_format="pcm",
    ) as response:
        buffer = b""
        for chunk in response.iter_bytes(chunk_size=4096):
            buffer += chunk

        audio = np.frombuffer(buffer, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio, samplerate=24000)
        sd.wait()
