from dipsy_dolphin.core.controller_models import AssistantTurn
from dipsy_dolphin.core.emotion import EmotionState
from dipsy_dolphin.ui.presentation_policy import (
    resolve_busy_note_presentation,
    resolve_loading_presentation,
    resolve_turn_presentation,
    resolve_waiting_presentation,
)


def test_joke_dialogue_category_resolves_to_laugh_and_joke_bubble() -> None:
    cue = resolve_turn_presentation(
        AssistantTurn(dialogue_category="joke"),
        emotion=EmotionState(excitement=80),
    )

    assert cue.animation_state == "laugh"
    assert cue.bubble_style.style_id == "joke"
    assert cue.delivery.queue_policy == "queue"
    assert cue.delivery.reveal_mode == "staged"


def test_thought_dialogue_category_resolves_to_talk_without_ui_wait_pose() -> None:
    cue = resolve_turn_presentation(
        AssistantTurn(dialogue_category="thought"),
        emotion=EmotionState(),
    )

    assert cue.animation_state == "talk"
    assert cue.bubble_style.style_id == "thought"
    assert cue.delivery.queue_policy == "drop"
    assert cue.delivery.replaceable is True


def test_waiting_presentation_uses_think_animation_and_thought_bubble() -> None:
    cue = resolve_waiting_presentation(emotion=EmotionState())

    assert cue.animation_state == "think"
    assert cue.dialogue_category == "thought"
    assert cue.bubble_style.style_id == "thought"
    assert cue.delivery.replaceable is True


def test_loading_presentation_uses_loading_animation() -> None:
    cue = resolve_loading_presentation(emotion=EmotionState())

    assert cue.animation_state == "loading"
    assert cue.dialogue_category == "status"
    assert cue.bubble_style.style_id == "status"


def test_busy_note_presentation_uses_alert_style_when_confident_enough() -> None:
    cue = resolve_busy_note_presentation(emotion=EmotionState(confidence=55))

    assert cue.animation_state == "surprised"
    assert cue.bubble_style.style_id == "alert"
    assert cue.delivery.queue_policy == "replace"
    assert cue.delivery.reveal_mode == "instant"


def test_scene_kind_celebration_prefers_joke_bubble_and_scene_animation() -> None:
    cue = resolve_turn_presentation(
        AssistantTurn(dialogue_category="normal", scene_kind="celebration"),
        emotion=EmotionState(excitement=55),
    )

    assert cue.scene_kind == "celebration"
    assert cue.animation_state == "laugh"
    assert cue.bubble_style.style_id == "joke"
    assert cue.delivery.hold_ms > 2200


def test_scene_kind_idea_prefers_thought_bubble_when_category_is_generic() -> None:
    cue = resolve_turn_presentation(
        AssistantTurn(dialogue_category="normal", scene_kind="idea"),
        emotion=EmotionState(confidence=50),
    )

    assert cue.scene_kind == "idea"
    assert cue.animation_state == "surprised"
    assert cue.bubble_style.style_id == "thought"


def test_dialogue_category_remains_primary_over_scene_bubble_choice() -> None:
    cue = resolve_turn_presentation(
        AssistantTurn(dialogue_category="alert", scene_kind="celebration"),
        emotion=EmotionState(excitement=80),
    )

    assert cue.bubble_style.style_id == "alert"
