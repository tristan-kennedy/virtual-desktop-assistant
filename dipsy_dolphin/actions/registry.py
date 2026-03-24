from dataclasses import dataclass
from typing import Any

from ..core.controller_models import ActionRequest


@dataclass(frozen=True)
class RegisteredAction:
    action_id: str
    description: str
    risk_level: str = "low"


REGISTERED_ACTIONS = {
    "roam_somewhere": RegisteredAction(
        action_id="roam_somewhere",
        description="Move Dipsy to another spot on screen.",
    ),
    "idle": RegisteredAction(
        action_id="idle",
        description="Stay present without speaking or moving.",
    ),
}


def allowed_action_names() -> tuple[str, ...]:
    return tuple(REGISTERED_ACTIONS)


def sanitize_action_request(
    action_id: str | None, args: dict[str, Any] | None = None
) -> ActionRequest | None:
    if not action_id:
        return None
    if action_id not in REGISTERED_ACTIONS:
        return None
    return ActionRequest(action_id=action_id, args=args or {})
