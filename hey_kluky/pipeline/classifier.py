from hey_kluky.classifiers import classify as _classify


def classify(text: str) -> str:
    result = _classify(text)
    return result["intent"]
