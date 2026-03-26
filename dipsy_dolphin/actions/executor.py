from __future__ import annotations

from typing import Protocol

from ..core.controller_models import ActionRequest
from .models import ExecutionResult
from .registry import get_registered_action


class ActionExecutorProtocol(Protocol):
    def execute(self, request: ActionRequest) -> ExecutionResult: ...


class ActionExecutor:
    def execute(self, request: ActionRequest) -> ExecutionResult:
        registered_action = get_registered_action(request.action_id)
        if registered_action is None:
            message = "That routine is not on Dipsy's approved stage list."
            return ExecutionResult(
                action_id=request.action_id,
                status="rejected",
                message=message,
                observation={
                    "action_id": request.action_id,
                    "status": "rejected",
                    "message": message,
                    "args": dict(request.args),
                },
            )

        unexpected_args = tuple(
            key for key in sorted(request.args) if key not in registered_action.allowed_args
        )
        if unexpected_args:
            message = (
                "That routine arrived with unexpected arguments: "
                + ", ".join(unexpected_args)
                + "."
            )
            return ExecutionResult(
                action_id=request.action_id,
                status="rejected",
                message=message,
                observation={
                    "action_id": request.action_id,
                    "status": "rejected",
                    "message": message,
                    "args": dict(request.args),
                },
            )

        if registered_action.handler is None:
            message = "That routine exists on paper but has no stage machinery behind it yet."
            return ExecutionResult(
                action_id=request.action_id,
                status="failed",
                message=message,
                observation={
                    "action_id": request.action_id,
                    "status": "failed",
                    "message": message,
                    "args": dict(request.args),
                },
            )

        try:
            directive = registered_action.handler(request.args)
        except Exception as exc:
            message = f"Dipsy's stage machinery jammed: {exc}"
            return ExecutionResult(
                action_id=request.action_id,
                status="failed",
                message=message,
                observation={
                    "action_id": request.action_id,
                    "status": "failed",
                    "message": message,
                    "args": dict(request.args),
                },
            )

        return ExecutionResult(
            action_id=request.action_id,
            status="success",
            message=registered_action.description,
            directive=directive,
            observation={
                "action_id": request.action_id,
                "status": "success",
                "message": registered_action.description,
                "args": dict(request.args),
                "directive_kind": directive.kind,
            },
        )
