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
    pose_id: str = "idle"
    expression_id: str = "neutral"
    eye_state: str = "open"
    mouth_state: str = "closed"
    facing: str = "right"
    active_effects: Tuple[str, ...] = field(default_factory=tuple)
    bob_offset: int = 0
    style_variant: str = "flat-retro"
