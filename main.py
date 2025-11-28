import openwakeword
import openwakeword.utils
from openwakeword.model import Model
from openwakeword.vad import VAD
from pvrecorder import PvRecorder
import numpy as np
import httpx
import time
import typer
import os
from datetime import datetime
from pydub import AudioSegment

app = typer.Typer()

def trigger_api(model_name: str):
    print(f"\n⚡ {model_name} detected! Triggering API...")
    try:
        api_url = "http://localhost:8000/trigger"
        httpx.post(api_url, json={"command": "activate"})
        print("✅ API Request Sent (Simulated)")
    except Exception as e:
        print(f"❌ API Error: {e}")

def record_until_silence(recorder: PvRecorder, output_dir: str, silence_timeout: float, max_duration: float) -> str:
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
        if vad_score > 0.5:
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
    
    # Create AudioSegment
    audio_segment = AudioSegment(
        data=audio_data,
        sample_width=2, # 16-bit
        frame_rate=16000,
        channels=1
    )
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"recording_{timestamp}.mp3")
    
    # Export as MP3
    audio_segment.export(filename, format="mp3")
    print(f"💾 Saved recording to: {filename}")
    return filename

@app.command()
def main(
    model_name: str = typer.Option("hey_jarvis", help="The wake word model to use."),
    threshold: float = typer.Option(0.5, help="Confidence threshold (0.0 to 1.0)."),
    output_dir: str = typer.Option("./recordings", help="Directory to save recorded audio."),
    silence_timeout: float = typer.Option(1.0, help="Seconds of silence to stop recording."),
    max_duration: float = typer.Option(30.0, help="Maximum recording duration in seconds."),
    ww_vad_threshold: float = typer.Option(0.01, help="VAD threshold for wake word detection (0.0 to 1.0). Set > 0 to enable."),
    noise_suppression: bool = typer.Option(False, help="Enable Speex noise suppression (Linux only).")
):
    print("Loading models... (this might take a moment first time)")
    openwakeword.utils.download_models(model_names=[model_name])
    
    model = Model(
        wakeword_models=[model_name],
        vad_threshold=ww_vad_threshold if ww_vad_threshold > 0 else None,
        enable_speex_noise_suppression=noise_suppression
    )

    recorder = PvRecorder(device_index=-1, frame_length=1280)
    recorder.start()

    print(f"🎤 Listening for '{model_name}' locally... (Ctrl+C to stop)")
    if ww_vad_threshold > 0:
        print("\t(VAD Enabled: threshold={ww_vad_threshold})")
    if noise_suppression:
        print("\t(Noise Suppression Enabled)")

    try:
        while True:
            pcm = recorder.read()
            audio_data = np.array(pcm, dtype=np.int16)
            prediction = model.predict(audio_data)
            for m_name, score in prediction.items():
                if score > threshold:
                    record_until_silence(recorder, output_dir, silence_timeout, max_duration)
                    trigger_api(model_name)
                    model.reset()
                    print(f"🎤 Listening for '{model_name}' locally... (Ctrl+C to stop)")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        recorder.stop()
        recorder.delete()

if __name__ == "__main__":
    app()