from dataclasses import dataclass, field
from typing import Tuple


Point = Tuple[int, int]


@dataclass(frozen=True)
class CharacterBounds:
    width: int
    height: int
    bubble_anchor: Point
    feet_anchor: Point
    look_anchor: Point


@dataclass(frozen=True)
class CharacterPresentation:
    """Renderer-facing output after presentation resolution.

    `pose_id` is the resolved body pose for the renderer.
    `expression_id` is the resolved facial expression.
    Neither field is a model-facing animation request.
    """

    pose_id: str = "idle"
    expression_id: str = "neutral"
    eye_state: str = "open"
    mouth_state: str = "closed"
    facing: str = "right"
    active_effects: Tuple[str, ...] = field(default_factory=tuple)
    bob_offset: int = 0
    accent_variant: str = "calm"
    style_variant: str = "flat-retro"


@dataclass(frozen=True)
class BubbleStyle:
    style_id: str = "normal"
    background_color: str = "#FFF7E6"
    border_color: str = "#1B263B"
    text_color: str = "#102226"
    border_style: str = "solid"
    min_width: int = 220
    max_width: int = 420


@dataclass(frozen=True)
class DialogueDelivery:
    reveal_mode: str = "staged"
    chunk_chars: int = 28
    chunk_pause_ms: int = 150
    hold_ms: int = 2200
    interrupt_priority: int = 3
    queue_policy: str = "queue"
    replaceable: bool = False


@dataclass(frozen=True)
class ResolvedTurnPresentation:
    """UI-facing presentation cue derived from a semantic assistant turn.

    `animation_state` is a transient animation request for the state machine.
    `dialogue_category` remains the speech/content classification.
    `scene_kind` is optional theatrical framing layered on top of the turn.
    """

    animation_state: str = "talk"
    bubble_style: BubbleStyle = field(default_factory=BubbleStyle)
    dialogue_category: str = "normal"
    scene_kind: str = ""
    delivery: DialogueDelivery = field(default_factory=DialogueDelivery)
