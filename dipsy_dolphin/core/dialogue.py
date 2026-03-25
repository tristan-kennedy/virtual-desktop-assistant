from __future__ import annotations


DIALOGUE_CATEGORIES = (
    "normal",
    "joke",
    "question",
    "status",
    "alert",
    "onboarding",
    "thought",
)


def normalize_dialogue_category(value: object, *, fallback: str = "normal") -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in DIALOGUE_CATEGORIES:
        return cleaned
    return fallback
