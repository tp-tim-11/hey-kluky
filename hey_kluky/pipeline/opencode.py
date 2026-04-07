import httpx

from hey_kluky.config import config


def create_session() -> str:
    with httpx.Client(base_url=config.OPENCODE_URL, timeout=30) as client:
        response = client.post("/session", json={"title": "Test Text session"})
        response.raise_for_status()
        data = response.json()
        print(f"[DEBUG] create_session response: {data}")
        httpx.post(f"{config.OPENCODE_URL}/tui/select-session", json={"sessionID": data["id"]})
        return data["id"]


def send_message(text: str, directory: str, session_id: str | None = None) -> tuple[str, str]:
    if not session_id:
        session_id = create_session()

    payload = {
        "directory": directory,
        "mode": "plan",
        "parts": [{"type": "text", "text": text}],
    }

    with httpx.Client(base_url=config.OPENCODE_URL, timeout=180) as client:
        response = client.post(
            f"/session/{session_id}/message",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        print(f"[DEBUG] send_message response: {data}")

    parts = data.get("parts", data.get("data", {}).get("parts", []))
    output = "".join(p["text"] for p in parts if p.get("type") == "text")

    return session_id, output
