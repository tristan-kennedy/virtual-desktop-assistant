from __future__ import annotations

from collections.abc import Callable

from ..actions.models import ExecutionResult


def apply_execution_result(
    execution_result: ExecutionResult | None,
    *,
    start_walk: Callable[[], bool],
    request_quit: Callable[[], bool],
) -> bool:
    if execution_result is None or execution_result.status != "success":
        return False
    if execution_result.directive is None:
        return False
    if execution_result.directive.kind == "noop":
        return False
    if execution_result.directive.kind == "start_walk":
        return start_walk()
    if execution_result.directive.kind == "request_quit":
        return request_quit()
    return False
