import json

import anthropic

from hey_kluky.settings import settings

_client: anthropic.Anthropic | None = None

VALID_INTENTS = ("new_session", "clear_history", "none")

SYSTEM_PROMPT = """You are a voice command intent classifier. Given a user's voice transcript, classify it into one of these intents:

- "new_session": The user wants to start a new conversation, session, or chat.
  Examples: "start a new session", "new conversation", "begin fresh", "start over", "new chat", "open a new chat".
- "clear_history": The user wants to clear, reset, or wipe the current chat history.
  Examples: "clear chat history", "reset the chat", "wipe the conversation", "delete the history", "forget everything", "clean slate".
- "none": Anything else — the user is making a normal request or statement that should be forwarded to the current session.

Important rules:
- "new_session" and "clear_history" both indicate the user wants a fresh start, but use "clear_history" when the user specifically mentions clearing/deleting/wiping history, and "new_session" when they ask for a new chat/session/conversation.
- Only return "new_session" or "clear_history" if the user clearly and explicitly wants to start fresh. Phrases like "I don't want a new session" or "keep this session" should return "none".
- When in doubt, return "none".

Respond with ONLY a JSON object, e.g. {"intent": "new_session"} or {"intent": "clear_history"} or {"intent": "none"}
No other text."""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def classify(transcript: str) -> dict:
    """Classify a voice transcript into an intent.

    Returns {"intent": "new_session" | "none"}.
    On any failure, returns {"intent": "none"} to avoid blocking the user.
    """
    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": transcript}],
        )
        text = response.content[0].text.strip()
        result = json.loads(text)
        if result.get("intent") in VALID_INTENTS:
            return result
        return {"intent": "none"}
    except Exception as e:
        print(f"⚠️ Intent classifier error (falling back to none): {e}")
        return {"intent": "none"}
