import sounddevice as sd
from fastapi import HTTPException, Request

from hey_kluky.settings import settings
from hey_kluky.server import app
from hey_kluky.server.models import TestRequest, TestResponse, TriggerResponse
from hey_kluky.server.processing import (
    bytes_to_audio_file,
    get_openai_client,
    _process_text,
)


@app.post("/trigger", response_model=TriggerResponse)
async def trigger_endpoint(request: Request):
    try:
        audio_bytes = await request.body()

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="No audio data provided")

        print(f"📥 Received audio: {len(audio_bytes)} bytes")

        client = get_openai_client()

        audio_file = bytes_to_audio_file(audio_bytes, format="wav")

        try:
            transcription = client.audio.transcriptions.create(
                model=settings.WHISPER_MODEL,
                file=audio_file,
                language=settings.WHISPER_LANGUAGE,
            )
            print(f"✅ Transcription received: {transcription.text}")
        except Exception as whisper_error:
            print(f"❌ Whisper API Error: {whisper_error}")
            return TriggerResponse(
                success=False,
                error=f"Whisper API Error: {str(whisper_error)}",
            )

        result = _process_text(transcription.text)

        return TriggerResponse(
            success=True,
            transcription=transcription.text,
            sdk_result=result["sdk_result"],
        )

    except HTTPException:
        raise
    except Exception as e:
        return TriggerResponse(
            success=False,
            error=str(e),
        )


@app.post("/test", response_model=TestResponse)
async def test_endpoint(body: TestRequest):
    try:
        print(f"🧪 Test input: {body.text}")
        result = _process_text(body.text)
        return TestResponse(
            success=True,
            intent=result["intent"],
            session_id=result["session_id"],
            text_input=body.text,
            sdk_result=result["sdk_result"],
        )
    except Exception as e:
        return TestResponse(
            success=False,
            text_input=body.text,
            error=str(e),
        )


@app.post("/stop-tts")
async def stop_tts():
    sd.stop()
    return {"success": True}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "api_key_configured": bool(settings.OPENAI_API_KEY)}
