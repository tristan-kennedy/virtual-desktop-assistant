from dipsy_dolphin.core.emotion import EmotionState
from dipsy_dolphin.ui.presentation_controller import PresentationController


def test_joke_speech_resolves_to_happy_laugh_pose() -> None:
    controller = PresentationController()

    controller.set_animation_state("laugh")
    controller.set_dialogue_category("joke")
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


def test_loading_pose_uses_loading_effect() -> None:
    controller = PresentationController()

    controller.set_animation_state("loading")
    presentation = controller.resolve()

    assert presentation.pose_id == "loading"
    assert presentation.expression_id == "happy"
    assert "loading" in presentation.active_effects


def test_surprised_question_pose_uses_open_mouth_and_question_effect() -> None:
    controller = PresentationController()

    controller.set_animation_state("surprised")
    controller.set_dialogue_category("question")
    presentation = controller.resolve()

    assert presentation.pose_id == "surprised"
    assert presentation.expression_id == "concerned"
    assert presentation.mouth_state == "talk_open"
    assert "question" in presentation.active_effects


def test_high_excitement_adds_spark_and_happy_bias() -> None:
    controller = PresentationController()

    controller.set_animation_state("idle")
    controller.set_emotion(EmotionState(excitement=82, energy=78, confidence=55))
    presentation = controller.resolve()

    assert presentation.expression_id == "happy"
    assert "spark" in presentation.active_effects
    assert presentation.bob_offset == 3
    assert presentation.accent_variant == "warm"


def test_low_confidence_uses_concerned_expression() -> None:
    controller = PresentationController()

    controller.set_animation_state("idle")
    controller.set_emotion(EmotionState(confidence=18, excitement=20, familiarity=10))
    presentation = controller.resolve()

    assert presentation.expression_id == "concerned"
    assert presentation.accent_variant == "wary"


def test_scene_kind_celebration_overlays_happy_laugh_pose() -> None:
    controller = PresentationController()

    controller.set_animation_state("talk")
    controller.set_scene_kind("celebration")
    presentation = controller.resolve()

    assert presentation.pose_id == "laugh"
    assert presentation.expression_id == "happy"
    assert "spark" in presentation.active_effects


def test_scene_kind_panic_overlays_concerned_surprised_pose() -> None:
    controller = PresentationController()

    controller.set_animation_state("idle")
    controller.set_scene_kind("panic")
    presentation = controller.resolve()

    assert presentation.pose_id == "surprised"
    assert presentation.expression_id == "concerned"
    assert "sweat" in presentation.active_effects
