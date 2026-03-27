from __future__ import annotations

from typing import Protocol

from ..core.controller_models import ActionRequest
from ..desktop import create_default_desktop_backend
from ..desktop.backend import DesktopBackendProtocol
from .models import ExecutionResult
from .registry import validate_action_request


class ActionExecutorProtocol(Protocol):
    def execute(self, request: ActionRequest) -> ExecutionResult: ...


class ActionExecutor:
    def __init__(self, desktop_backend: DesktopBackendProtocol | None = None) -> None:
        self.desktop_backend = desktop_backend or create_default_desktop_backend()

    def execute(self, request: ActionRequest) -> ExecutionResult:
        validation = validate_action_request(request.action_id, request.args)
        registered_action = validation.action
        if registered_action is None:
            message = validation.error or "That routine is not on Dipsy's approved stage list."
            return ExecutionResult(
                action_id=request.action_id,
                status="rejected",
                message=message,
                observation=self._build_observation(
                    request=request,
                    status="rejected",
                    message=message,
                    operation=request.action_id,
                    failure_reason=message,
                ),
            )

        if validation.error:
            message = validation.error
            return ExecutionResult(
                action_id=request.action_id,
                status="rejected",
                message=message,
                observation=self._build_observation(
                    request=request,
                    status="rejected",
                    message=message,
                    operation=registered_action.action_id,
                    failure_reason=message,
                ),
            )

        if registered_action.execution_surface == "desktop":
            return self._execute_desktop_action(request, validation.args)

        if registered_action.handler is None:
            message = "That routine exists on paper but has no stage machinery behind it yet."
            return ExecutionResult(
                action_id=request.action_id,
                status="failed",
                message=message,
                observation=self._build_observation(
                    request=request,
                    status="failed",
                    message=message,
                    operation=registered_action.action_id,
                    failure_reason=message,
                ),
            )

        try:
            directive = registered_action.handler(validation.args)
        except Exception as exc:
            message = f"Dipsy's stage machinery jammed: {exc}"
            return ExecutionResult(
                action_id=request.action_id,
                status="failed",
                message=message,
                observation=self._build_observation(
                    request=request,
                    status="failed",
                    message=message,
                    operation=registered_action.action_id,
                    failure_reason=str(exc),
                ),
            )

        return ExecutionResult(
            action_id=request.action_id,
            status="success",
            message=registered_action.description,
            directive=directive,
            observation=self._build_observation(
                request=request,
                status="success",
                message=registered_action.description,
                operation=registered_action.action_id,
                directive_kind=directive.kind,
            ),
        )

    def _execute_desktop_action(
        self,
        request: ActionRequest,
        args: dict[str, object],
    ) -> ExecutionResult:
        try:
            if request.action_id == "focus_or_open_app":
                result = self.desktop_backend.focus_or_open_app(str(args["app_id"]))
            elif request.action_id == "browser_search":
                result = self.desktop_backend.browser_search(str(args["query"]))
            elif request.action_id == "open_url":
                result = self.desktop_backend.open_url(str(args["url"]))
            elif request.action_id == "open_path":
                result = self.desktop_backend.open_path(str(args["path"]))
            else:
                message = "That desktop routine has no executor wiring."
                return ExecutionResult(
                    action_id=request.action_id,
                    status="failed",
                    message=message,
                    observation=self._build_observation(
                        request=request,
                        status="failed",
                        message=message,
                        operation=request.action_id,
                        failure_reason=message,
                    ),
                )
        except Exception as exc:
            message = f"Dipsy's desktop machinery jammed: {exc}"
            return ExecutionResult(
                action_id=request.action_id,
                status="failed",
                message=message,
                observation=self._build_observation(
                    request=request,
                    status="failed",
                    message=message,
                    operation=request.action_id,
                    failure_reason=str(exc),
                ),
            )

        return ExecutionResult(
            action_id=request.action_id,
            status=result.status,
            message=result.message,
            observation=self._build_observation(
                request=request,
                status=result.status,
                message=result.message,
                operation=result.operation,
                target=result.target,
                resolved_app_id=result.resolved_app_id,
                launched=result.launched,
                focused=result.focused,
                opened=result.opened,
                failure_reason=result.failure_reason,
            ),
        )

    def _build_observation(
        self,
        *,
        request: ActionRequest,
        status: str,
        message: str,
        operation: str,
        target: str = "",
        resolved_app_id: str = "",
        launched: bool = False,
        focused: bool = False,
        opened: bool = False,
        failure_reason: str = "",
        directive_kind: str = "",
    ) -> dict[str, object]:
        observation: dict[str, object] = {
            "action_id": request.action_id,
            "status": status,
            "message": message,
            "args": dict(request.args),
            "operation": operation,
            "target": target,
            "resolved_app_id": resolved_app_id,
            "launched": launched,
            "focused": focused,
            "opened": opened,
            "failure_reason": failure_reason,
        }
        if directive_kind:
            observation["directive_kind"] = directive_kind
        return observation
