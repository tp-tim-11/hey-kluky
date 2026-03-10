import re
from pathlib import Path

from hey_kluky.config import config
from hey_kluky.pipeline import stt, classifier, opencode, tts
from hey_kluky.api import start_server, _tts_lock


def _summarize_for_speech(text: str, max_sentences: int = 3) -> str:
    """Strip code blocks and truncate to first few sentences for spoken output."""
    text = re.sub(r"```[\s\S]*?```", "", text).strip()
    text = re.sub(r"`[^`]+`", "", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:max_sentences])


def run_text(text: str):
    """Run the pipeline once with text input (skip wakeword + STT)."""
    session_id = None
    session_id, response = _process(text, session_id)
    if response:
        short = _summarize_for_speech(response)
        try:
            with _tts_lock:
                tts.speak(short)
        except Exception as e:
            print(f"\u26a0\ufe0f TTS unavailable: {e}")
    return response


def run_voice(
    model_name: str = "hey_jarvis",
    threshold: float = 0.5,
    silence_timeout: float = 2.0,
    max_duration: float = 60.0,
    ww_vad_threshold: float = 0.01,
    noise_suppression: bool = False,
):
    """Main voice loop: wakeword -> record -> STT -> classify -> opencode -> TTS."""
    from hey_kluky.wakeword import init_wakeword, wait_for_wakeword, record_until_silence

    recorder, model = init_wakeword(
        model_name=model_name,
        threshold=threshold,
        ww_vad_threshold=ww_vad_threshold,
        noise_suppression=noise_suppression,
    )

    start_server(config.API_HOST, config.API_PORT)

    session_id = None
    print(f"\U0001f3a4 Listening for '{model_name}'... (Ctrl+C to stop)")

    try:
        while True:
            wait_for_wakeword(recorder, model, model_name, threshold)
            tts.stop()

            audio_bytes = record_until_silence(recorder, silence_timeout, max_duration)

            try:
                text = stt.transcribe(audio_bytes)
            except Exception as e:
                print(f"\u274c STT Error: {e}")
                print(f"\U0001f3a4 Listening for '{model_name}'... (Ctrl+C to stop)")
                continue

            if not text.strip():
                print("\u26a0\ufe0f  No speech detected.")
                print(f"\U0001f3a4 Listening for '{model_name}'... (Ctrl+C to stop)")
                continue

            print(f"\U0001f4dd Transcription: {text}")
            session_id, response = _process(text, session_id)

            if response:
                short = _summarize_for_speech(response)
                try:
                    with _tts_lock:
                        tts.speak(short)
                except Exception as e:
                    print(f"\u274c TTS Error: {e}")

            print(f"\U0001f3a4 Listening for '{model_name}'... (Ctrl+C to stop)")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        recorder.stop()
        recorder.delete()


def _process(text: str, session_id: str | None) -> tuple[str | None, str | None]:
    """Classify intent and route to opencode. Returns (session_id, response)."""
    test_dir = str((Path.cwd() / config.TEST_OPENCODE_DIR).resolve())

    intent = classifier.classify(text)
    print(f"\U0001f9e0 Intent: {intent} (session: {session_id})")

    if intent in ("new_session", "clear_history"):
        try:
            session_id = opencode.create_session()
            print(f"\U0001f4cc New session: {session_id}")
            msg = "Started new session." if intent == "new_session" else "Chat history cleared. Started fresh session."
            return session_id, msg
        except Exception as e:
            print(f"\u274c OpenCode Error: {e}")
            return None, f"Error creating session: {e}"

    try:
        session_id, response = opencode.send_message(text, test_dir, session_id)
        print(f"\U0001f4cc Session: {session_id}")
        print(f"\U0001f916 Response: {response[:200]}..." if len(response) > 200 else f"\U0001f916 Response: {response}")
        return session_id, response
    except Exception as e:
        print(f"\u274c OpenCode Error: {e}")
        return session_id, f"Error: {e}"
