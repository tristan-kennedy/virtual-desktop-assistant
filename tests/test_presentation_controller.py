from dipsy_dolphin.ui.presentation_controller import PresentationController


def test_joke_speech_resolves_to_happy_talk_pose() -> None:
    controller = PresentationController()

    controller.start_speech("joke")
    presentation = controller.resolve()

    assert presentation.pose_id == "talk"
    assert presentation.expression_id == "happy"
    assert presentation.mouth_state == "talk_open"
    assert "spark" in presentation.active_effects


def test_thinking_pose_uses_question_effect() -> None:
    controller = PresentationController()

    controller.set_thinking()
    presentation = controller.resolve()

    assert presentation.pose_id == "think"
    assert presentation.expression_id == "concerned"
    assert "question" in presentation.active_effects


def test_stopping_speech_returns_to_walk_state() -> None:
    controller = PresentationController()

    controller.set_walking(-18)
    controller.start_speech("normal")
    controller.stop_speech()
    presentation = controller.resolve()

    assert presentation.pose_id == "walk"
    assert presentation.facing == "left"
    assert presentation.expression_id == "happy"
