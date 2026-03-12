import io
import os
import subprocess
import threading
from pathlib import Path

from fastapi import HTTPException
from openai import OpenAI

from hey_kluky.settings import settings
from hey_kluky.tts import speak
from hey_kluky.classifiers import classify
from hey_kluky.server import state

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SDK_SCRIPT = _PROJECT_ROOT / "opencode-sdk" / "index.js"
TEST_OPENCODE_DIR = (_PROJECT_ROOT / settings.TEST_OPENCODE_DIR).resolve()


def _sdk_env() -> dict[str, str]:
    env = os.environ.copy()
    env["OPENCODE_PROVIDER_ID"] = settings.OPENCODE_PROVIDER_ID
    env["OPENCODE_MODEL_ID"] = settings.OPENCODE_MODEL_ID
    return env


def get_openai_client() -> OpenAI:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    kwargs = {"api_key": settings.OPENAI_API_KEY}
    if settings.OPENAI_API_BASE:
        kwargs["base_url"] = settings.OPENAI_API_BASE

    return OpenAI(**kwargs)


def bytes_to_audio_file(audio_bytes: bytes, format: str = "mp3"):
    audio_buffer = io.BytesIO(audio_bytes)
    audio_buffer.name = f"audio.{format}"
    return audio_buffer


def _process_text(text: str) -> dict:
    """Shared logic: intent classification -> subprocess call -> session parsing.

    Returns dict with keys: intent, session_id, sdk_result.
    """
    intent_result = classify(text)
    intent = intent_result["intent"]
    print(f"🧠 Intent: {intent} (active_session: {state.active_session_id})")

    # Both "new_session" and "clear_history" start a fresh opencode session
    # without forwarding the meta-command text to the LLM
    if intent in ("new_session", "clear_history"):
        state.active_session_id = None
        print(f"🔄 Resetting session (intent: {intent})")

        sdk_result = None
        try:
            cmd = ["node", str(SDK_SCRIPT), "--create-only"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(_PROJECT_ROOT),
                encoding="utf-8",
                env=_sdk_env(),
            )
            if result.stdout:
                print(f"📤 SDK Output:\n{result.stdout}")
            if result.stderr:
                print(f"📋 SDK Logs:\n{result.stderr}")

            if result.returncode == 0:
                stdout_lines = [
                    line for line in result.stdout.strip().split("\n") if line.strip()
                ]
                if stdout_lines and stdout_lines[0].startswith("SESSION:"):
                    state.active_session_id = stdout_lines[0][len("SESSION:") :]
                    print(f"📌 Active session: {state.active_session_id}")

                if intent == "new_session":
                    sdk_result = "Started new session."
                else:
                    sdk_result = "Chat history cleared. Started fresh session."
            else:
                sdk_result = f"Error: {result.stderr.strip()}"
                print(f"❌ SDK Error: {result.stderr.strip()}")
        except Exception as sdk_error:
            sdk_result = f"SDK Error: {str(sdk_error)}"
            print(f"❌ SDK Error: {sdk_error}")

        if (
            sdk_result
            and not sdk_result.startswith("Error:")
            and not sdk_result.startswith("SDK Error:")
        ):
            threading.Thread(target=speak, args=(sdk_result,), daemon=True).start()

        return {
            "intent": intent,
            "session_id": state.active_session_id,
            "sdk_result": sdk_result,
        }

    # Normal branch: forward text to SDK
    sdk_result = None
    try:
        cmd = ["node", str(SDK_SCRIPT), text, str(TEST_OPENCODE_DIR)]
        if state.active_session_id:
            cmd.append(state.active_session_id)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(_PROJECT_ROOT),
            encoding="utf-8",
            env=_sdk_env(),
        )
        if result.stdout:
            print(f"📤 SDK Output:\n{result.stdout}")
        if result.stderr:
            print(f"📋 SDK Logs:\n{result.stderr}")

        if result.returncode == 0:
            stdout_lines = [
                line for line in result.stdout.strip().split("\n") if line.strip()
            ]

            new_session_id = None
            response_lines = stdout_lines
            if stdout_lines and stdout_lines[0].startswith("SESSION:"):
                new_session_id = stdout_lines[0][len("SESSION:") :]
                response_lines = stdout_lines[1:]

            if new_session_id:
                state.active_session_id = new_session_id
                print(f"📌 Active session: {state.active_session_id}")

            sdk_result = "\n".join(response_lines)
            print(f"🤖 SDK Result: {sdk_result}")
        else:
            sdk_result = f"Error: {result.stderr.strip()}"
            print(f"❌ SDK Error: {result.stderr.strip()}")
    except Exception as sdk_error:
        sdk_result = f"SDK Error: {str(sdk_error)}"
        print(f"❌ SDK Error: {sdk_error}")

    if (
        sdk_result
        and not sdk_result.startswith("Error:")
        and not sdk_result.startswith("SDK Error:")
    ):
        threading.Thread(target=speak, args=(sdk_result,), daemon=True).start()

    return {
        "intent": intent,
        "session_id": state.active_session_id,
        "sdk_result": sdk_result,
    }
