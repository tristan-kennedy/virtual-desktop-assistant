from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..core.controller_models import ActionRequest
from ..desktop.catalog import allowed_app_ids
from .models import ExecutionDirective


QUERY_MAX_LENGTH = 240
URL_MAX_LENGTH = 2048
PATH_MAX_LENGTH = 4096


@dataclass(frozen=True)
class ActionArgSpec:
    name: str
    kind: str
    description: str
    required: bool = True
    choices: tuple[str, ...] = ()
    max_length: int | None = None

    def prompt_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind,
            "description": self.description,
            "required": self.required,
        }
        if self.choices:
            payload["choices"] = list(self.choices)
        if self.max_length is not None:
            payload["max_length"] = self.max_length
        return payload


@dataclass(frozen=True)
class RegisteredAction:
    action_id: str
    description: str
    risk_level: str = "low"
    arg_specs: tuple[ActionArgSpec, ...] = ()
    execution_surface: str = "handler"
    handler: Callable[[dict[str, Any]], ExecutionDirective] | None = None

    def prompt_payload(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "description": self.description,
            "risk_level": self.risk_level,
            "args": {spec.name: spec.prompt_payload() for spec in self.arg_specs},
        }


@dataclass(frozen=True)
class ActionValidationResult:
    action: RegisteredAction | None
    args: dict[str, Any]
    error: str = ""

    @property
    def is_valid(self) -> bool:
        return self.action is not None and not self.error


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
    "focus_or_open_app": RegisteredAction(
        action_id="focus_or_open_app",
        description="Focus a supported desktop app window or open it if needed.",
        risk_level="low",
        arg_specs=(
            ActionArgSpec(
                name="app_id",
                kind="enum",
                description="Stable supported app id.",
                choices=allowed_app_ids(),
            ),
        ),
        execution_surface="desktop",
    ),
    "browser_search": RegisteredAction(
        action_id="browser_search",
        description="Open a web search in the default browser.",
        risk_level="low",
        arg_specs=(
            ActionArgSpec(
                name="query",
                kind="string",
                description="Search query text.",
                max_length=QUERY_MAX_LENGTH,
            ),
        ),
        execution_surface="desktop",
    ),
    "open_url": RegisteredAction(
        action_id="open_url",
        description="Open an http or https URL in the default browser.",
        risk_level="low",
        arg_specs=(
            ActionArgSpec(
                name="url",
                kind="url",
                description="Absolute http or https URL.",
                max_length=URL_MAX_LENGTH,
            ),
        ),
        execution_surface="desktop",
    ),
    "open_path": RegisteredAction(
        action_id="open_path",
        description="Open an existing local file or folder.",
        risk_level="low",
        arg_specs=(
            ActionArgSpec(
                name="path",
                kind="path",
                description="Existing local file or folder path.",
                max_length=PATH_MAX_LENGTH,
            ),
        ),
        execution_surface="desktop",
    ),
}


def allowed_action_names() -> tuple[str, ...]:
    return tuple(REGISTERED_ACTIONS)


def get_registered_action(action_id: str) -> RegisteredAction | None:
    return REGISTERED_ACTIONS.get(action_id)


def action_prompt_payload() -> list[dict[str, object]]:
    return [action.prompt_payload() for action in REGISTERED_ACTIONS.values()]


def validate_action_request(
    action_id: str | None, args: dict[str, Any] | None = None
) -> ActionValidationResult:
    if not action_id:
        return ActionValidationResult(
            action=None,
            args={},
            error="That routine is not on Dipsy's approved stage list.",
        )

    registered_action = get_registered_action(action_id)
    if registered_action is None:
        return ActionValidationResult(
            action=None,
            args={},
            error="That routine is not on Dipsy's approved stage list.",
        )

    validated_args, error = _validate_action_args(registered_action, args or {})
    return ActionValidationResult(
        action=registered_action,
        args=validated_args,
        error=error,
    )


def sanitize_action_request(
    action_id: str | None, args: dict[str, Any] | None = None
) -> ActionRequest | None:
    validation = validate_action_request(action_id, args)
    if not validation.is_valid or validation.action is None:
        return None
    return ActionRequest(action_id=validation.action.action_id, args=validation.args)


def _validate_action_args(
    action: RegisteredAction, args: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    if not isinstance(args, dict):
        return {}, "That routine arrived with malformed arguments."

    known_names = {spec.name for spec in action.arg_specs}
    unexpected_args = tuple(key for key in sorted(args) if key not in known_names)
    if unexpected_args:
        return (
            {},
            "That routine arrived with unexpected arguments: "
            + ", ".join(unexpected_args)
            + ".",
        )

    validated: dict[str, Any] = {}
    for spec in action.arg_specs:
        if spec.required and spec.name not in args:
            return {}, f"That routine is missing required argument: {spec.name}."
        if spec.name not in args:
            continue
        value, error = _sanitize_arg_value(spec, args[spec.name])
        if error:
            return {}, error
        validated[spec.name] = value
    return validated, ""


def _sanitize_arg_value(spec: ActionArgSpec, value: Any) -> tuple[Any, str]:
    if spec.kind == "enum":
        normalized = str(value).strip().lower()
        if not normalized:
            return "", f"Argument '{spec.name}' must not be empty."
        if normalized not in spec.choices:
            return "", f"Argument '{spec.name}' must be one of: {', '.join(spec.choices)}."
        return normalized, ""

    text = str(value).strip()
    if not text:
        return "", f"Argument '{spec.name}' must not be empty."
    if spec.max_length is not None and len(text) > spec.max_length:
        return "", f"Argument '{spec.name}' is too long."

    if spec.kind == "string":
        return text, ""

    if spec.kind == "url":
        parsed = urlparse(text)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "", f"Argument '{spec.name}' must be an http or https URL."
        return text, ""

    if spec.kind == "path":
        expanded = os.path.expandvars(os.path.expanduser(text))
        candidate = Path(expanded)
        if not candidate.exists():
            return "", f"Argument '{spec.name}' must point to an existing local path."
        try:
            return str(candidate.resolve()), ""
        except OSError:
            return str(candidate.absolute()), ""

    return "", f"Argument '{spec.name}' uses an unsupported type."
