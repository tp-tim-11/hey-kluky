from pathlib import Path

from hey_kluky.config import config
from hey_kluky.pipeline import stt, opencode, tts
from hey_kluky.pipeline.timer import timer
from hey_kluky.api import start_server, take_pending_session, wait_for_tts


def run_text(
    text: str,
    api_host: str = config.API_HOST,
    api_port: int = config.API_PORT,
):
    """Run the pipeline once with text input — same as voice mode but without wakeword + STT."""
    start_server(api_host, api_port)

    session_id = None
    timer.start_cycle()
    tts.play_wait_music()
    timer.start("LLM")
    session_id, response = _process(text, session_id)

    # Wait for TTS to finish (triggered via /v1/speak endpoint)
    wait_for_tts()
    timer.print_summary()

    return response


def run_voice(
    model_name: str = config.WAKEWORD_MODEL_NAME,
    threshold: float = 0.5,
    silence_timeout: float = 2.0,
    max_duration: float = 60.0,
    ww_vad_threshold: float = 0.01,
    noise_suppression: bool = False,
    api_host: str = config.API_HOST,
    api_port: int = config.API_PORT,
):
    """Main voice loop: wakeword -> record -> STT -> opencode -> TTS (called asi API)."""
    from hey_kluky.wakeword import init_wakeword, wait_for_wakeword, record_until_silence

    recorder, model = init_wakeword(
        model_name=model_name,
        threshold=threshold,
        ww_vad_threshold=ww_vad_threshold,
        noise_suppression=noise_suppression,
    )

    start_server(api_host, api_port)

    session_id = None
    print(f"Listening for '{model_name}'... (Ctrl+C to stop)")

    try:
        while True:
            timer.start_cycle()
            timer.start("Wakeword")
            wait_for_wakeword(recorder, model, model_name, threshold)
            tts.stop()
            tts.play_confirmation()

            # Check if the API created a new session
            pending = take_pending_session()
            if pending:
                session_id = pending
                print(f"New session from API: {session_id}")

            timer.start("Recording")
            audio_bytes = record_until_silence(
                recorder, silence_timeout, max_duration)

            timer.start("STT")
            try:
                text = stt.transcribe(audio_bytes)
            except Exception as e:
                print(f"STT Error: {e}")
                print(f"Listening for '{model_name}'... (Ctrl+C to stop)")
                continue

            if not text.strip():
                print("No speech detected.")
                print(f"Listening for '{model_name}'... (Ctrl+C to stop)")
                continue

            print(f"Transcription: {text}")
            tts.play_wait_music()
            timer.start("LLM")
            session_id, response = _process(text, session_id)
            
            # Wait for TTS (runs in background thread via API)
            wait_for_tts()
            timer.print_summary()
            print(f"Listening for '{model_name}'... (Ctrl+C to stop)")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        recorder.stop()
        recorder.delete()


# def _is_new_session_response(response: str) -> bool:
#     """Check if the server response indicates the LLM wants to start a new session."""
#     return response.strip().lower() == "new_session"


def _process(text: str, session_id: str | None) -> tuple[str | None, str | None]:
    """Send message to opencode. If server replies 'new_session', create a fresh session."""
    test_dir = str((Path.cwd() / config.TEST_OPENCODE_DIR).resolve())

    try:
        session_id, response = opencode.send_message(
            text, test_dir, session_id)
        print(f"Session: {session_id}")

        # if _is_new_session_response(response):
        #     session_id = opencode.create_session()
        #     print(f"New session: {session_id}")
        #     return session_id, "Started new session."

        print(f"Response: {response[:200]}..." if len(
            response) > 200 else f"Response: {response}")
        return session_id, response
    except Exception as e:
        print(f"OpenCode Error: {e}")
        return session_id, f"Error: {e}"
