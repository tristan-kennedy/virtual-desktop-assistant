import os

from PySide6.QtWidgets import QApplication

from dipsy_dolphin.ui.character_widget import CharacterWidget
from dipsy_dolphin.ui.presentation_models import CharacterPresentation


def test_character_widget_switches_to_talk_only_after_idle_loop_finishes() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    widget = CharacterWidget()
    widget.animation_timer.stop()
    widget._active_pose_id = "idle"
    widget._pending_pose_id = "idle"
    widget._frame_index = 22

    widget.set_presentation(CharacterPresentation(pose_id="talk"))

    widget._advance_frame()
    assert widget._active_pose_id == "idle"
    assert widget._frame_index == 23

    widget._advance_frame()
    assert widget._active_pose_id == "talk"
    assert widget._frame_index == 0
    assert app is not None


def test_character_widget_emits_pose_activated_when_loop_boundary_switches_pose() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    widget = CharacterWidget()
    widget.animation_timer.stop()
    widget._active_pose_id = "idle"
    widget._pending_pose_id = "talk"
    widget._frame_index = 23
    activated: list[str] = []
    widget.pose_presented.connect(activated.append)

    widget._advance_frame()
    widget.paintEvent(None)

    assert widget._active_pose_id == "talk"
    assert activated == ["talk"]
    assert app is not None


def test_character_widget_uses_idle_when_requested_pose_has_no_frames() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    widget = CharacterWidget()
    widget.animation_timer.stop()

    widget.set_presentation(CharacterPresentation(pose_id="surprised"))

    assert widget._pending_pose_id == "idle"
    assert app is not None
