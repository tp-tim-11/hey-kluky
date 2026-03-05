"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = ""
    ANTHROPIC_API_KEY: str = ""
    WHISPER_MODEL: str = "whisper-1"
    WHISPER_LANGUAGE: str = "en"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    TEST_OPENCODE_DIR: str = ""

    def validate(self) -> bool:
        if not self.OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY not set in environment or .env file")
            return False
        return True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


settings = Settings()
