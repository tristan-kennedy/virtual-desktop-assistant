from dipsy_dolphin.actions.executor import ActionExecutor
from dipsy_dolphin.core.controller_models import ActionRequest
from dipsy_dolphin.desktop.models import DesktopOperationResult


class FakeDesktopBackend:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def focus_or_open_app(self, app_id: str) -> DesktopOperationResult:
        self.calls.append(("focus_or_open_app", app_id))
        return DesktopOperationResult(
            operation="focus_or_open_app",
            target=app_id,
            resolved_app_id=app_id,
            status="success",
            message=f"Focused {app_id}.",
            focused=True,
        )

    def browser_search(self, query: str) -> DesktopOperationResult:
        self.calls.append(("browser_search", query))
        return DesktopOperationResult(
            operation="browser_search",
            target=query,
            resolved_app_id="browser",
            status="success",
            message=f"Searched for {query}.",
            launched=True,
            opened=True,
        )

    def open_url(self, url: str) -> DesktopOperationResult:
        self.calls.append(("open_url", url))
        return DesktopOperationResult(
            operation="open_url",
            target=url,
            resolved_app_id="browser",
            status="success",
            message=f"Opened {url}.",
            launched=True,
            opened=True,
        )

    def open_path(self, path: str) -> DesktopOperationResult:
        self.calls.append(("open_path", path))
        return DesktopOperationResult(
            operation="open_path",
            target=path,
            resolved_app_id="explorer",
            status="success",
            message=f"Opened {path}.",
            launched=True,
            opened=True,
        )


def test_action_executor_rejects_unknown_action_id() -> None:
    executor = ActionExecutor(desktop_backend=FakeDesktopBackend())

    result = executor.execute(ActionRequest(action_id="not-real", args={}))

    assert result.status == "rejected"
    assert result.directive is None
    assert result.observation["action_id"] == "not-real"
    assert result.observation["status"] == "rejected"


def test_action_executor_rejects_unexpected_args() -> None:
    executor = ActionExecutor(desktop_backend=FakeDesktopBackend())

    result = executor.execute(ActionRequest(action_id="idle", args={"loud": True}))

    assert result.status == "rejected"
    assert "unexpected arguments" in result.message
    assert result.observation["args"] == {"loud": True}


def test_action_executor_returns_noop_for_idle() -> None:
    executor = ActionExecutor(desktop_backend=FakeDesktopBackend())

    result = executor.execute(ActionRequest(action_id="idle", args={}))

    assert result.status == "success"
    assert result.directive is not None
    assert result.directive.kind == "noop"
    assert result.observation["directive_kind"] == "noop"


def test_action_executor_returns_start_walk_for_roam() -> None:
    executor = ActionExecutor(desktop_backend=FakeDesktopBackend())

    result = executor.execute(ActionRequest(action_id="roam_somewhere", args={}))

    assert result.status == "success"
    assert result.directive is not None
    assert result.directive.kind == "start_walk"
    assert result.observation["directive_kind"] == "start_walk"


def test_action_executor_returns_request_quit_for_quit_app() -> None:
    executor = ActionExecutor(desktop_backend=FakeDesktopBackend())

    result = executor.execute(ActionRequest(action_id="quit_app", args={}))

    assert result.status == "success"
    assert result.directive is not None
    assert result.directive.kind == "request_quit"
    assert result.observation["directive_kind"] == "request_quit"


def test_action_executor_dispatches_browser_search_to_desktop_backend() -> None:
    backend = FakeDesktopBackend()
    executor = ActionExecutor(desktop_backend=backend)

    result = executor.execute(ActionRequest(action_id="browser_search", args={"query": "dolphins"}))

    assert result.status == "success"
    assert backend.calls == [("browser_search", "dolphins")]
    assert result.observation["operation"] == "browser_search"
    assert result.observation["target"] == "dolphins"
    assert result.observation["resolved_app_id"] == "browser"
    assert result.observation["opened"] is True


def test_action_executor_rejects_invalid_url_before_desktop_backend_runs() -> None:
    backend = FakeDesktopBackend()
    executor = ActionExecutor(desktop_backend=backend)

    result = executor.execute(ActionRequest(action_id="open_url", args={"url": "file:///tmp/nope"}))

    assert result.status == "rejected"
    assert "http or https URL" in result.message
    assert backend.calls == []


def test_action_executor_rejects_missing_path_before_desktop_backend_runs(tmp_path) -> None:
    backend = FakeDesktopBackend()
    executor = ActionExecutor(desktop_backend=backend)

    result = executor.execute(
        ActionRequest(action_id="open_path", args={"path": str(tmp_path / "missing.txt")})
    )

    assert result.status == "rejected"
    assert "existing local path" in result.message
    assert backend.calls == []


def test_action_executor_focus_or_open_app_uses_stable_app_id() -> None:
    backend = FakeDesktopBackend()
    executor = ActionExecutor(desktop_backend=backend)

    result = executor.execute(
        ActionRequest(action_id="focus_or_open_app", args={"app_id": "notepad"})
    )

    assert result.status == "success"
    assert backend.calls == [("focus_or_open_app", "notepad")]
    assert result.observation["focused"] is True
    assert result.observation["resolved_app_id"] == "notepad"
