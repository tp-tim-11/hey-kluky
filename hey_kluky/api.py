import threading

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel

from hey_kluky.pipeline import tts, opencode

app = FastAPI()
v1 = APIRouter(prefix="/v1")

_tts_lock = threading.Lock()

# Shared session state — the API can write a new session_id here,
# and the orchestrator reads (and clears) it each loop iteration.
_session_lock = threading.Lock()
_pending_session_id: str | None = None


class SpeakRequest(BaseModel):
    text: str


def speak_in_background(text: str):
    """Run TTS in a background thread so it doesn't block the caller."""
    def _run():
        try:
            with _tts_lock:
                tts.speak(text)
        except Exception as e:
            print(f"TTS Error: {e}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


@v1.post("/speak")
def speak(req: SpeakRequest):
    if _tts_lock.locked():
        raise HTTPException(status_code=409, detail="TTS is already playing")
    speak_in_background(req.text)
    return {"status": "ok"}


@v1.get("/new_session")
def new_session():
    """Create a new opencode session. The orchestrator will pick up the new ID."""
    global _pending_session_id
    try:
        sid = opencode.create_session()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    with _session_lock:
        _pending_session_id = sid
    return {"status": "ok"}


def take_pending_session() -> str | None:
    """Return and clear the pending session ID (called by the orchestrator)."""
    global _pending_session_id
    with _session_lock:
        sid = _pending_session_id
        _pending_session_id = None
        return sid


app.include_router(v1)


def start_server(host: str = "0.0.0.0", port: int = 8321):
    import uvicorn

    thread = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={"host": host, "port": port, "log_level": "warning"},
        daemon=True,
    )
    thread.start()
    print(f"API server started on {host}:{port}")
    return thread
