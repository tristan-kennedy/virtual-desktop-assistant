import json

from ..actions.registry import sanitize_action_request
from ..core.controller_models import AssistantTurn
from .prompt_builder import ALLOWED_ANIMATIONS


ALLOWED_SPEECH_STYLES = {
    "normal",
    "joke",
    "question",
    "spark",
    "alert",
    "status",
    "onboarding",
}

ALLOWED_BEHAVIORS = {
    "idle",
    "emote",
    "quip",
    "question",
    "joke",
    "roam",
    "chat",
    "status",
    "reset",
    "onboarding",
    "action",
}


def parse_assistant_turn(payload: dict[str, object] | str) -> AssistantTurn:
    parsed = _coerce_payload(payload)

    say = str(parsed.get("say", "")).strip()
    animation = str(parsed.get("animation", "talk")).strip().lower() or "talk"
    if animation not in ALLOWED_ANIMATIONS:
        animation = "talk"

    speech_style = str(parsed.get("speech_style", "normal")).strip().lower() or "normal"
    if speech_style not in ALLOWED_SPEECH_STYLES:
        speech_style = "normal"

    behavior = str(parsed.get("behavior", "")).strip().lower()
    if behavior not in ALLOWED_BEHAVIORS:
        behavior = ""

    cooldown_ms = _bounded_int(parsed.get("cooldown_ms", 12000), minimum=4000, maximum=30000)
    topic = str(parsed.get("topic", "chat")).strip().lower() or "chat"

    action_payload = parsed.get("action")
    action = None
    if isinstance(action_payload, dict):
        action = sanitize_action_request(
            str(action_payload.get("action_id", "")).strip() or None,
            action_payload.get("args") if isinstance(action_payload.get("args"), dict) else None,
        )

    return AssistantTurn(
        say=say,
        animation=animation,
        speech_style=speech_style,
        action=action,
        cooldown_ms=cooldown_ms,
        behavior=behavior,
        topic=topic,
        source="llm",
    )


def extract_json_object(payload: str) -> dict[str, object]:
    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        loaded = json.loads(_extract_first_json_object(payload))

    if not isinstance(loaded, dict):
        raise ValueError("Local model payload must be a JSON object")
    return loaded


def _coerce_payload(payload: dict[str, object] | str) -> dict[str, object]:
    if isinstance(payload, dict):
        return payload
    return extract_json_object(payload)


def _extract_first_json_object(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].lstrip()

    start = cleaned.find("{")
    if start == -1:
        raise ValueError("Invalid JSON from local model")

    depth = 0
    in_string = False
    escaping = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if escaping:
            escaping = False
            continue
        if char == "\\":
            escaping = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start : index + 1]

    raise ValueError("Invalid JSON from local model")


def _bounded_int(value: object, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, (int, float, str)):
        return minimum
    try:
        number = int(value)
    except (TypeError, ValueError):
        return minimum
    return max(minimum, min(maximum, number))
