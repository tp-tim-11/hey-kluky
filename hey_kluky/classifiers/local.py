"""Keyword-based intent classifier (no API key required).

Same interface as hey_kluky.classifiers.llm.classify() so they can be swapped.
For the LLM-powered version, see hey_kluky.classifiers.llm.
"""

import re

NEGATIVE_PREFIXES = re.compile(
    r"\b(don'?t|do not|keep|no)\b", re.IGNORECASE
)

NEW_SESSION_PHRASES = [
    "new session",
    "new conversation",
    "new chat",
    "start over",
    "begin fresh",
    "start fresh",
    "fresh start",
]

CLEAR_HISTORY_PHRASES = [
    "clear history",
    "clear chat",
    "reset chat",
    "wipe conversation",
    "delete history",
    "forget everything",
    "clean slate",
    "reset the conversation",
]


def classify(transcript: str) -> dict:
    """Classify a voice transcript into an intent using keyword matching.

    Returns {"intent": "new_session" | "clear_history" | "none"}.
    """
    text = transcript.lower().strip()

    # If the sentence contains a negative prefix, don't trigger any intent
    if NEGATIVE_PREFIXES.search(text):
        return {"intent": "none"}

    for phrase in CLEAR_HISTORY_PHRASES:
        if phrase in text:
            return {"intent": "clear_history"}

    for phrase in NEW_SESSION_PHRASES:
        if phrase in text:
            return {"intent": "new_session"}

    return {"intent": "none"}
