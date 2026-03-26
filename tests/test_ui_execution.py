from dipsy_dolphin.actions.models import ExecutionDirective, ExecutionResult
from dipsy_dolphin.ui.execution import apply_execution_result


def test_apply_execution_result_triggers_walk_for_start_walk() -> None:
    calls: list[str] = []

    applied = apply_execution_result(
        ExecutionResult(
            action_id="roam_somewhere",
            status="success",
            directive=ExecutionDirective(kind="start_walk"),
        ),
        start_walk=lambda: calls.append("walk") or True,
        request_quit=lambda: calls.append("quit") or True,
    )

    assert applied is True
    assert calls == ["walk"]


def test_apply_execution_result_ignores_non_successful_results() -> None:
    calls: list[str] = []

    applied = apply_execution_result(
        ExecutionResult(action_id="roam_somewhere", status="rejected"),
        start_walk=lambda: calls.append("walk") or True,
        request_quit=lambda: calls.append("quit") or True,
    )

    assert applied is False
    assert calls == []


def test_apply_execution_result_requests_quit_for_request_quit() -> None:
    calls: list[str] = []

    applied = apply_execution_result(
        ExecutionResult(
            action_id="quit_app",
            status="success",
            directive=ExecutionDirective(kind="request_quit"),
        ),
        start_walk=lambda: calls.append("walk") or True,
        request_quit=lambda: calls.append("quit") or True,
    )

    assert applied is True
    assert calls == ["quit"]
