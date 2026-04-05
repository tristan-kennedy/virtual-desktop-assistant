from types import SimpleNamespace

from dipsy_dolphin.ui.app import AssistantApp
from dipsy_dolphin.ui.dialogue_presenter import DialoguePresenter
from dipsy_dolphin.ui.presentation_models import BubbleStyle, DialogueDelivery, ResolvedTurnPresentation


class _TimerStub:
    def __init__(self) -> None:
        self.started_with: int | None = None
        self.active = False

    def start(self, duration_ms: int) -> None:
        self.started_with = duration_ms
        self.active = True

    def stop(self) -> None:
        self.active = False

    def isActive(self) -> bool:
        return self.active


class _BubbleWindowStub:
    def __init__(self) -> None:
        self.hidden = False
        self.shown = False
        self.text = ""

    def show_text(self, text: str, style=None) -> None:
        self.text = text

    def show(self) -> None:
        self.shown = True

    def raise_(self) -> None:
        return None

    def hide(self) -> None:
        self.hidden = True


def _cue() -> ResolvedTurnPresentation:
    return ResolvedTurnPresentation(
        animation_state="idle",
        bubble_style=BubbleStyle(style_id="normal"),
        dialogue_category="normal",
        delivery=DialogueDelivery(reveal_mode="instant", hold_ms=1200),
    )


def test_show_active_dialogue_waits_for_speech_pose_before_showing_bubble_or_voice() -> None:
    app = SimpleNamespace()
    app.dialogue_presenter = DialoguePresenter()
    app.dialogue_presenter.enqueue("Hello there", _cue(), utterance_id="speech-1")
    app.current_dialogue_category = None
    app.current_scene_kind = ""
    app._dialogue_waiting_for_pose_id = ""
    app.character_widget = SimpleNamespace(
        manifest=SimpleNamespace(speech_pose_id="talk"),
        resolve_pose_id=lambda pose_id: pose_id,
        is_pose_active=lambda pose_id: False,
    )
    app.bubble_window = _BubbleWindowStub()
    app.dialogue_reveal_timer = _TimerStub()
    app.bubble_hide_timer = _TimerStub()
    app._request_calls = []
    app._request_animation = lambda state, duration_ms=None, force=False: app._request_calls.append(
        (state, duration_ms, force)
    )
    app._position_bubble = lambda: None
    app._ensure_active_voice = lambda: (_ for _ in ()).throw(AssertionError("voice should wait"))
    app._clear_animation_overlay = lambda: None
    app._sync_presentation_to_motion = lambda: None
    app._dialogue_pose_id = lambda cue: "talk"
    app._dialogue_can_start = lambda pose_id: False
    app._wait_for_dialogue_pose = lambda pose_id: setattr(app, "_dialogue_waiting_for_pose_id", pose_id)

    AssistantApp._show_active_dialogue(app)

    assert app._request_calls
    assert app._request_calls[0][0] == "talk"
    assert app._dialogue_waiting_for_pose_id == "talk"
    assert app.bubble_window.shown is False
    assert app.bubble_window.text == ""


def test_pose_presented_callback_retries_dialogue_start_when_pose_becomes_ready() -> None:
    app = SimpleNamespace()
    app._dialogue_waiting_for_pose_id = "talk"
    app.dialogue_presenter = SimpleNamespace(active_item=object())
    calls: list[str] = []
    app._show_active_dialogue = lambda: calls.append("show")

    AssistantApp._on_character_pose_presented(app, "talk")

    assert app._dialogue_waiting_for_pose_id == ""
    assert calls == ["show"]
