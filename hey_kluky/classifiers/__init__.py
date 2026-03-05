import os

# Use local keyword-based classifier by default (no API key needed).
# Set USE_LOCAL_CLASSIFIER=false in .env to use the LLM classifier instead.
if os.environ.get("USE_LOCAL_CLASSIFIER", "true").lower() != "false":
    from hey_kluky.classifiers.local import classify
else:
    from hey_kluky.classifiers.llm import classify

__all__ = ["classify"]
