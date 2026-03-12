"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = ""

    WHISPER_MODEL: str = "whisper-1"
    WHISPER_LANGUAGE: str = "sk"

    OPENCODE_URL: str = "http://localhost:4096"
    OPENCODE_PROVIDER_ID: str = "github-copilot"
    OPENCODE_MODEL_ID: str = "gpt-4.1"
    TEST_OPENCODE_DIR: str = "./test_opencode"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    WAKEWORD_MODEL_NAME: str = "hey_kluky"
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "pNInz6obpgDQGcFmaJgB"
    ELEVENLABS_MODEL_ID: str = "eleven_turbo_v2_5"

    @classmethod
    def validate(self) -> bool:
        if not self.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not set in environment or .env file")
            return False
        return True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


config = Settings()
