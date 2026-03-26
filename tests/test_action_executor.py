from dipsy_dolphin.actions.executor import ActionExecutor
from dipsy_dolphin.core.controller_models import ActionRequest


def test_action_executor_rejects_unknown_action_id() -> None:
    executor = ActionExecutor()

    result = executor.execute(ActionRequest(action_id="not-real", args={}))

    assert result.status == "rejected"
    assert result.directive is None
    assert result.observation["action_id"] == "not-real"
    assert result.observation["status"] == "rejected"


def test_action_executor_rejects_unexpected_args() -> None:
    executor = ActionExecutor()

    result = executor.execute(ActionRequest(action_id="idle", args={"loud": True}))

    assert result.status == "rejected"
    assert "unexpected arguments" in result.message
    assert result.observation["args"] == {"loud": True}


def test_action_executor_returns_noop_for_idle() -> None:
    executor = ActionExecutor()

    result = executor.execute(ActionRequest(action_id="idle", args={}))

    assert result.status == "success"
    assert result.directive is not None
    assert result.directive.kind == "noop"
    assert result.observation["directive_kind"] == "noop"


def test_action_executor_returns_start_walk_for_roam() -> None:
    executor = ActionExecutor()

    result = executor.execute(ActionRequest(action_id="roam_somewhere", args={}))

    assert result.status == "success"
    assert result.directive is not None
    assert result.directive.kind == "start_walk"
    assert result.observation["directive_kind"] == "start_walk"


def test_action_executor_returns_request_quit_for_quit_app() -> None:
    executor = ActionExecutor()

    result = executor.execute(ActionRequest(action_id="quit_app", args={}))

    assert result.status == "success"
    assert result.directive is not None
    assert result.directive.kind == "request_quit"
    assert result.observation["directive_kind"] == "request_quit"
