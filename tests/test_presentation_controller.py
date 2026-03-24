from dipsy_dolphin.ui.presentation_controller import PresentationController


def test_joke_speech_resolves_to_happy_laugh_pose() -> None:
    controller = PresentationController()

    controller.set_animation_state("laugh")
    controller.set_speech_style("joke")
    presentation = controller.resolve()

    assert presentation.pose_id == "laugh"
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


def test_surprised_question_pose_uses_open_mouth_and_question_effect() -> None:
    controller = PresentationController()

    controller.set_animation_state("surprised")
    controller.set_speech_style("question")
    presentation = controller.resolve()

    assert presentation.pose_id == "surprised"
    assert presentation.expression_id == "concerned"
    assert presentation.mouth_state == "talk_open"
    assert "question" in presentation.active_effects
