import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "whisper-1")
    WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "sk")
    TEST_OPENCODE_DIR: str = os.getenv("TEST_OPENCODE_DIR", "./test_opencode")
    OPENCODE_URL: str = os.getenv("OPENCODE_URL", "http://localhost:4096")
    OPENCODE_MODEL_ID: str = os.getenv("OPENCODE_MODEL_ID", "gpt-4.1")
    OPENCODE_PROVIDER_ID: str = os.getenv("OPENCODE_PROVIDER_ID", "github-copilot")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8321"))

    @classmethod
    def validate(cls) -> bool:
        if not cls.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not set in environment or .env file")
            return False
        return True


config = Config()
