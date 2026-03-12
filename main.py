import typer
from hey_kluky.orchestrator import run_voice, run_text

app = typer.Typer()


@app.command()
def main(
    text: str | None = typer.Option(None, help="Run pipeline once with text input (skip wakeword + STT)."),
    model_name: str = typer.Option("hey-kluky", help="The wake word model to use."),
    threshold: float = typer.Option(0.5, help="Confidence threshold (0.0 to 1.0)."),
    silence_timeout: float = typer.Option(2.0, help="Seconds of silence to stop recording."),
    max_duration: float = typer.Option(60.0, help="Maximum recording duration in seconds."),
    ww_vad_threshold: float = typer.Option(0.01, help="VAD threshold for wake word detection."),
    noise_suppression: bool = typer.Option(False, help="Enable Speex noise suppression (Linux only)."),
    api_host: str = typer.Option("0.0.0.0", help="API server host."),
    api_port: int = typer.Option(8321, help="API server port."),
):
    if text:
        response = run_text(text)
        if response:
            print(f"Response: {response}")
    else:
        run_voice(
            model_name=model_name,
            threshold=threshold,
            silence_timeout=silence_timeout,
            max_duration=max_duration,
            ww_vad_threshold=ww_vad_threshold,
            noise_suppression=noise_suppression,
            api_host=api_host,
            api_port=api_port,
        )


if __name__ == "__main__":
    app()
