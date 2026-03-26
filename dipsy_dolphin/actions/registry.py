from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..core.controller_models import ActionRequest
from .models import ExecutionDirective


@dataclass(frozen=True)
class RegisteredAction:
    action_id: str
    description: str
    risk_level: str = "low"
    allowed_args: tuple[str, ...] = ()
    handler: Callable[[dict[str, Any]], ExecutionDirective] | None = None


def _idle_handler(_args: dict[str, Any]) -> ExecutionDirective:
    return ExecutionDirective(kind="noop")


def _roam_handler(_args: dict[str, Any]) -> ExecutionDirective:
    return ExecutionDirective(kind="start_walk")


def _quit_handler(_args: dict[str, Any]) -> ExecutionDirective:
    return ExecutionDirective(kind="request_quit")


REGISTERED_ACTIONS = {
    "roam_somewhere": RegisteredAction(
        action_id="roam_somewhere",
        description="Move Dipsy to another spot on screen.",
        handler=_roam_handler,
    ),
    "idle": RegisteredAction(
        action_id="idle",
        description="Stay present without speaking or moving.",
        handler=_idle_handler,
    ),
    "quit_app": RegisteredAction(
        action_id="quit_app",
        description="Close Dipsy and shut down the app.",
        handler=_quit_handler,
    ),
}


def allowed_action_names() -> tuple[str, ...]:
    return tuple(REGISTERED_ACTIONS)


def get_registered_action(action_id: str) -> RegisteredAction | None:
    return REGISTERED_ACTIONS.get(action_id)


def sanitize_action_request(
    action_id: str | None, args: dict[str, Any] | None = None
) -> ActionRequest | None:
    if not action_id:
        return None
    if action_id not in REGISTERED_ACTIONS:
        return None
    return ActionRequest(action_id=action_id, args=args or {})
