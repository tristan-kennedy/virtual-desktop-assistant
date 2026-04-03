from dipsy_dolphin.core.controller_models import AssistantTurn, ControllerResult
from dipsy_dolphin.core.models import SessionState
from dipsy_dolphin.ui.app import AssistantApp


class DummyController:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def joke_turn(self, session: SessionState) -> ControllerResult:
        self.calls.append(f"joke:{session.__class__.__name__}")
        return ControllerResult(turn=AssistantTurn())

    def do_something_turn(self, session: SessionState) -> ControllerResult:
        self.calls.append(f"do_something:{session.__class__.__name__}")
        return ControllerResult(turn=AssistantTurn())

    def status_turn(self, session: SessionState) -> ControllerResult:
        self.calls.append(f"status:{session.__class__.__name__}")
        return ControllerResult(turn=AssistantTurn())


class DummyApp:
    pass


def _build_app_for_routine_test() -> tuple[DummyApp, DummyController, list[str]]:
    app = DummyApp()
    controller = DummyController()
    submitted_labels: list[str] = []

    app.session = SessionState()
    app.controller = controller
    app._note_user_interaction = lambda: None
    app._perform_controller_result = lambda result, schedule_idle=False: None
    app._show_busy_note = lambda: None

    def submit(label, task, on_result, *, progress_mode="llm_wait"):
        submitted_labels.append(label)
        task()
        return True

    app._submit_controller_task = submit
    return app, controller, submitted_labels


def test_tell_joke_uses_dedicated_controller_event() -> None:
    app, controller, submitted_labels = _build_app_for_routine_test()

    AssistantApp._tell_joke(app)

    assert submitted_labels == ["joke"]
    assert controller.calls == ["joke:SessionState"]


def test_random_bit_uses_dedicated_controller_event() -> None:
    app, controller, submitted_labels = _build_app_for_routine_test()

    AssistantApp._random_bit(app)

    assert submitted_labels == ["do something"]
    assert controller.calls == ["do_something:SessionState"]


def test_show_status_uses_dedicated_controller_event() -> None:
    app, controller, submitted_labels = _build_app_for_routine_test()

    AssistantApp._show_status(app)

    assert submitted_labels == ["status"]
    assert controller.calls == ["status:SessionState"]
