from __future__ import annotations

from typing import Protocol

from .models import DesktopOperationResult


class DesktopBackendProtocol(Protocol):
    def focus_or_open_app(self, app_id: str) -> DesktopOperationResult: ...

    def browser_search(self, query: str) -> DesktopOperationResult: ...

    def open_url(self, url: str) -> DesktopOperationResult: ...

    def open_path(self, path: str) -> DesktopOperationResult: ...


class UnavailableDesktopBackend:
    def __init__(self, reason: str = "Desktop control is only available on Windows.") -> None:
        self.reason = reason

    def focus_or_open_app(self, app_id: str) -> DesktopOperationResult:
        return self._unsupported("focus_or_open_app", target=app_id, resolved_app_id=app_id)

    def browser_search(self, query: str) -> DesktopOperationResult:
        return self._unsupported("browser_search", target=query)

    def open_url(self, url: str) -> DesktopOperationResult:
        return self._unsupported("open_url", target=url)

    def open_path(self, path: str) -> DesktopOperationResult:
        return self._unsupported("open_path", target=path)

    def _unsupported(
        self,
        operation: str,
        *,
        target: str = "",
        resolved_app_id: str = "",
    ) -> DesktopOperationResult:
        return DesktopOperationResult(
            operation=operation,
            target=target,
            resolved_app_id=resolved_app_id,
            status="failed",
            message=self.reason,
            failure_reason=self.reason,
        )
