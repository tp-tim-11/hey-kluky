from hey_kluky.settings import settings

# Use local keyword-based classifier by default (no API key needed).
# If ANTHROPIC_API_KEY is set, switch to the LLM classifier.
if settings.use_local_classifier:
    from hey_kluky.classifiers.local import classify
else:
    from hey_kluky.classifiers.llm import classify

__all__ = ["classify"]
