from pydantic import BaseModel


class TriggerResponse(BaseModel):
    success: bool
    transcription: str | None = None
    sdk_result: str | None = None
    error: str | None = None


class TestRequest(BaseModel):
    text: str


class TestResponse(BaseModel):
    success: bool
    intent: str | None = None
    session_id: str | None = None
    text_input: str | None = None
    sdk_result: str | None = None
    error: str | None = None
