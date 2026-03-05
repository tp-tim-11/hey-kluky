import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")
    WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "en")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    TEST_OPENCODE_DIR: str = os.getenv("TEST_OPENCODE_DIR", "./test_opencode")

    @classmethod
    def validate(cls) -> bool:
        if not cls.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not set in environment or .env file")
            return False
        return True


config = Config()
