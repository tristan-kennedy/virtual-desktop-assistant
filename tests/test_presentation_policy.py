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
