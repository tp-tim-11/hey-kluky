import io
import time

import numpy as np
import openwakeword
import openwakeword.utils
from openwakeword.model import Model
from openwakeword.vad import VAD
from pydub import AudioSegment
from pvrecorder import PvRecorder


def init_wakeword(
    model_name: str = "hey_jarvis",
    threshold: float = 0.5,
    ww_vad_threshold: float = 0.01,
    noise_suppression: bool = False,
) -> tuple[PvRecorder, Model]:
    print("Loading models... (this might take a moment the first time)")
    openwakeword.utils.download_models(model_names=[model_name])

    # model = Model(
    #     wakeword_models=[model_name],
    #     vad_threshold=ww_vad_threshold if ww_vad_threshold > 0 else None,
    #     enable_speex_noise_suppression=noise_suppression,
    # )

    model = Model(
        wakeword_models=["wakeword_model/hey_Klooky.onnx"],
        inference_framework="onnx",
        vad_threshold=ww_vad_threshold if ww_vad_threshold > 0 else None,
        enable_speex_noise_suppression=noise_suppression,
    )

    recorder = PvRecorder(device_index=-1, frame_length=1280)
    recorder.start()

    if ww_vad_threshold > 0:
        print(f"\t(VAD Enabled: threshold={ww_vad_threshold})")
    if noise_suppression:
        print("\t(Noise Suppression Enabled)")

    return recorder, model


def wait_for_wakeword(
    recorder: PvRecorder,
    model: Model,
    model_name: str,
    threshold: float,
):
    while True:
        pcm = recorder.read()
        audio_data = np.array(pcm, dtype=np.int16)
        prediction = model.predict(audio_data)
        for m_name, score in prediction.items():
            if score > threshold:
                print(f"\n\u26a1 Wake word detected!")
                model.reset()
                return


def record_until_silence(
    recorder: PvRecorder, silence_timeout: float, max_duration: float
) -> bytes:
    print(f"Recording... (Speak now, will stop after {silence_timeout}s of silence)")
    frames = []

    vad = VAD()

    start_time = time.time()
    last_speech_time = time.time()

    while True:
        pcm = recorder.read()
        frames.extend(pcm)

        audio_data = np.array(pcm, dtype=np.int16)
        vad_score = vad.predict(audio_data)

        current_time = time.time()

        if vad_score > 0.4:
            last_speech_time = current_time

        silence_duration = current_time - last_speech_time
        total_duration = current_time - start_time

        if silence_duration > silence_timeout:
            print(f"Silence detected ({silence_duration:.1f}s). Stopping.")
            break

        if total_duration > max_duration:
            print(f"Max duration reached ({max_duration}s). Stopping.")
            break

    audio_data = np.array(frames, dtype=np.int16).tobytes()

    audio_segment = AudioSegment(
        data=audio_data,
        sample_width=2,
        frame_rate=16000,
        channels=1,
    )

    wav_buffer = io.BytesIO()
    audio_segment.export(wav_buffer, format="wav")
    wav_bytes = wav_buffer.getvalue()

    print(f"Recorded {len(frames)} frames ({len(wav_bytes)} bytes)")
    return wav_bytes
