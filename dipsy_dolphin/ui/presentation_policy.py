from __future__ import annotations

from ..core.controller_models import AssistantTurn
from ..core.dialogue import normalize_dialogue_category
from ..core.emotion import EmotionState
from .presentation_models import BubbleStyle, DialogueDelivery, ResolvedTurnPresentation


BUBBLE_STYLES = {
    "normal": BubbleStyle(
        style_id="normal",
        background_color="#FFF7E6",
        border_color="#1B263B",
        text_color="#102226",
        min_width=220,
        max_width=420,
    ),
    "joke": BubbleStyle(
        style_id="joke",
        background_color="#FFF1BF",
        border_color="#D97706",
        text_color="#3A2208",
        min_width=230,
        max_width=380,
    ),
    "question": BubbleStyle(
        style_id="question",
        background_color="#E6F7FF",
        border_color="#2C7DA0",
        text_color="#12303E",
        min_width=230,
        max_width=380,
    ),
    "status": BubbleStyle(
        style_id="status",
        background_color="#E6FFFA",
        border_color="#0F766E",
        text_color="#113534",
        min_width=240,
        max_width=420,
    ),
    "alert": BubbleStyle(
        style_id="alert",
        background_color="#FDECEC",
        border_color="#C2410C",
        text_color="#421B12",
        min_width=240,
        max_width=360,
    ),
    "onboarding": BubbleStyle(
        style_id="onboarding",
        background_color="#F4F7D0",
        border_color="#5C7C2F",
        text_color="#23310D",
        min_width=240,
        max_width=400,
    ),
    "thought": BubbleStyle(
        style_id="thought",
        background_color="#EEF3F8",
        border_color="#4B6478",
        text_color="#20303D",
        border_style="dashed",
        min_width=220,
        max_width=340,
    ),
}

DELIVERY_PROFILES = {
    "normal": DialogueDelivery(
        reveal_mode="staged",
        chunk_chars=28,
        chunk_pause_ms=150,
        hold_ms=2200,
        interrupt_priority=3,
        queue_policy="queue",
        replaceable=False,
    ),
    "joke": DialogueDelivery(
        reveal_mode="staged",
        chunk_chars=24,
        chunk_pause_ms=180,
        hold_ms=3000,
        interrupt_priority=3,
        queue_policy="queue",
        replaceable=False,
    ),
    "question": DialogueDelivery(
        reveal_mode="staged",
        chunk_chars=24,
        chunk_pause_ms=160,
        hold_ms=2600,
        interrupt_priority=4,
        queue_policy="queue",
        replaceable=False,
    ),
    "status": DialogueDelivery(
        reveal_mode="staged",
        chunk_chars=26,
        chunk_pause_ms=180,
        hold_ms=3400,
        interrupt_priority=3,
        queue_policy="queue",
        replaceable=False,
    ),
    "alert": DialogueDelivery(
        reveal_mode="instant",
        chunk_chars=999,
        chunk_pause_ms=0,
        hold_ms=2400,
        interrupt_priority=5,
        queue_policy="replace",
        replaceable=False,
    ),
    "onboarding": DialogueDelivery(
        reveal_mode="staged",
        chunk_chars=24,
        chunk_pause_ms=160,
        hold_ms=3200,
        interrupt_priority=4,
        queue_policy="queue",
        replaceable=False,
    ),
    "thought": DialogueDelivery(
        reveal_mode="staged",
        chunk_chars=20,
        chunk_pause_ms=140,
        hold_ms=1600,
        interrupt_priority=1,
        queue_policy="drop",
        replaceable=True,
    ),
}


def resolve_turn_presentation(
    turn: AssistantTurn,
    *,
    emotion: EmotionState,
) -> ResolvedTurnPresentation:
    category = normalize_dialogue_category(turn.dialogue_category, fallback="normal")
    animation_state = _resolve_animation_state(
        requested_animation=turn.animation,
        dialogue_category=category,
        emotion=emotion,
    )
    bubble_style = BUBBLE_STYLES.get(category, BUBBLE_STYLES["normal"])
    return ResolvedTurnPresentation(
        animation_state=animation_state,
        bubble_style=bubble_style,
        dialogue_category=category,
        delivery=DELIVERY_PROFILES.get(category, DELIVERY_PROFILES["normal"]),
    )


def resolve_waiting_presentation(*, emotion: EmotionState) -> ResolvedTurnPresentation:
    return ResolvedTurnPresentation(
        animation_state=_resolve_animation_state(
            requested_animation="think",
            dialogue_category="thought",
            emotion=emotion,
        ),
        bubble_style=BUBBLE_STYLES["thought"],
        dialogue_category="thought",
        delivery=DELIVERY_PROFILES["thought"],
    )


def resolve_loading_presentation(*, emotion: EmotionState) -> ResolvedTurnPresentation:
    return ResolvedTurnPresentation(
        animation_state=_resolve_animation_state(
            requested_animation="loading",
            dialogue_category="status",
            emotion=emotion,
        ),
        bubble_style=BUBBLE_STYLES["status"],
        dialogue_category="status",
        delivery=DELIVERY_PROFILES["status"],
    )


def resolve_busy_note_presentation(*, emotion: EmotionState) -> ResolvedTurnPresentation:
    category = "alert" if emotion.confidence >= 25 else "thought"
    return ResolvedTurnPresentation(
        animation_state=_resolve_animation_state(
            requested_animation="surprised",
            dialogue_category=category,
            emotion=emotion,
        ),
        bubble_style=BUBBLE_STYLES[category],
        dialogue_category=category,
        delivery=DELIVERY_PROFILES[category],
    )


def _resolve_animation_state(
    *,
    requested_animation: str,
    dialogue_category: str,
    emotion: EmotionState,
) -> str:
    cleaned_animation = requested_animation.strip().lower()
    if cleaned_animation and cleaned_animation not in {"idle", "walk", "talk"}:
        return cleaned_animation

    if dialogue_category == "joke":
        return "laugh" if emotion.excitement >= 35 else "talk"
    if dialogue_category == "question":
        return "surprised"
    if dialogue_category == "status":
        return "sad" if emotion.energy <= 30 else "talk"
    if dialogue_category == "alert":
        return "sad" if emotion.confidence <= 25 else "surprised"
    if dialogue_category == "onboarding":
        return "excited" if emotion.familiarity >= 50 else "surprised"
    if dialogue_category == "thought":
        return "talk"
    if emotion.excitement >= 70:
        return "excited"
    if emotion.energy <= 25:
        return "sad"
    return "talk"
