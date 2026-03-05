import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hey_kluky.settings import settings

app = FastAPI(title="Whisper Transcription Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routes to register them on the app
from hey_kluky.server import routes  # noqa: E402, F401


def run():
    if not settings.validate():
        print("Warning: Server starting without valid API key configuration")

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
    )
