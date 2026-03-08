import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from hey_kluky.pipeline import tts

app = FastAPI()

_tts_lock = threading.Lock()


class SpeakRequest(BaseModel):
    text: str


@app.post("/speak")
def speak(req: SpeakRequest):
    acquired = _tts_lock.acquire(blocking=False)
    if not acquired:
        raise HTTPException(status_code=409, detail="TTS is already playing")
    try:
        tts.speak(req.text)
    finally:
        _tts_lock.release()
    return {"status": "ok"}


@app.post("/stop-tts")
def stop_tts():
    tts.stop()
    return {"status": "stopped"}


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
