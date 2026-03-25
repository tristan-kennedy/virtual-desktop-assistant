from dataclasses import dataclass, field
from typing import Optional, Tuple

from ..core.emotion import EmotionState
from .asset_manifest import load_character_manifest
from .presentation_models import CharacterPresentation


@dataclass
class PresentationSceneState:
    animation_state: str = "idle"
    dialogue_category: Optional[str] = None
    emotion: EmotionState = field(default_factory=EmotionState)
    facing: str = "right"
    extra_effects: Tuple[str, ...] = field(default_factory=tuple)


class PresentationController:
    def __init__(self) -> None:
        self.manifest = load_character_manifest()
        self.state = PresentationSceneState()

    def set_animation_state(self, state: str, delta_x: float = 0) -> None:
        self.state.animation_state = state
        self._set_facing_from_delta(delta_x)

    def set_dialogue_category(self, category: Optional[str]) -> None:
        self.state.dialogue_category = category

    def set_facing(self, facing: str) -> None:
        self.state.facing = facing

    def set_emotion(self, emotion: EmotionState) -> None:
        self.state.emotion = emotion.bounded()

    def set_extra_effects(self, effects: Tuple[str, ...]) -> None:
        self.state.extra_effects = effects

    def resolve(self) -> CharacterPresentation:
        pose_id = self.state.animation_state
        expression_id = "neutral"
        active_effects = list(self.state.extra_effects)
        mouth_state = "closed"
        bob_offset = 0
        eye_state = "open"
        accent_variant = "calm"

        if pose_id == "walk":
            expression_id = "happy"
        elif pose_id == "loading":
            expression_id = "happy"
            active_effects.append("loading")
        elif pose_id == "think":
            expression_id = "concerned"
            active_effects.append("question")
        elif pose_id == "laugh":
            expression_id = "happy"
            mouth_state = "talk_open"
            active_effects.append("spark")
        elif pose_id == "surprised":
            expression_id = "concerned"
            mouth_state = "talk_open"
            active_effects.append("question")
        elif pose_id == "sad":
            expression_id = "concerned"
        elif pose_id == "excited":
            expression_id = "happy"
            mouth_state = "talk_open"
            active_effects.append("spark")
        elif pose_id == "talk":
            mouth_state = "talk_open"

        if self.state.dialogue_category == "joke":
            expression_id = "happy"
            active_effects.append("spark")
            if pose_id == "idle":
                pose_id = "laugh"
                mouth_state = "talk_open"
        elif self.state.dialogue_category == "question":
            expression_id = "concerned"
            active_effects.append("question")
            if pose_id == "idle":
                pose_id = "surprised"
                mouth_state = "talk_open"
        elif self.state.dialogue_category == "onboarding":
            expression_id = "happy"
            active_effects.append("spark")
            if pose_id == "idle":
                pose_id = "surprised"
                mouth_state = "talk_open"
        elif self.state.dialogue_category == "alert":
            expression_id = "concerned"
            active_effects.append("sweat")
            if pose_id == "idle":
                pose_id = "surprised"
                mouth_state = "talk_open"
        elif self.state.dialogue_category == "thought":
            expression_id = "concerned"
            if pose_id == "idle":
                pose_id = "talk"
                mouth_state = "talk_open"
        elif self.state.dialogue_category == "status" and pose_id == "idle":
            pose_id = "talk"
            mouth_state = "talk_open"

        emotion = self.state.emotion.bounded()
        if emotion.excitement >= 65:
            active_effects.append("spark")
            bob_offset = 3
            accent_variant = "warm"
            if expression_id == "neutral":
                expression_id = "happy"
        elif emotion.energy <= 35:
            bob_offset = -1
            eye_state = "blink"
            accent_variant = "sleepy"

        if emotion.confidence <= 35 and expression_id == "neutral":
            expression_id = "concerned"
            accent_variant = "wary"
        if emotion.boredom >= 70 and pose_id == "idle":
            active_effects.append("question")
            accent_variant = "restless"
        if emotion.familiarity >= 60 and expression_id == "neutral":
            expression_id = "happy"
            if accent_variant == "calm":
                accent_variant = "friendly"

        return CharacterPresentation(
            pose_id=pose_id,
            expression_id=expression_id,
            eye_state=eye_state,
            mouth_state=mouth_state,
            facing=self.state.facing,
            active_effects=tuple(dict.fromkeys(active_effects)),
            bob_offset=bob_offset,
            accent_variant=accent_variant,
            style_variant=self.manifest.style_variant,
        )

    def set_idle(self, delta_x: float = 0) -> None:
        self.set_animation_state("idle", delta_x)

    def set_walking(self, delta_x: float) -> None:
        self.set_animation_state("walk", delta_x)

    def set_thinking(self, delta_x: float = 0) -> None:
        self.set_animation_state("think", delta_x)

    def start_speech(self, category: str = "normal") -> None:
        self.set_animation_state("talk")
        self.set_dialogue_category(category)

    def stop_speech(self) -> None:
        self.set_dialogue_category(None)

    def _set_facing_from_delta(self, delta_x: float) -> None:
        if delta_x > 1:
            self.state.facing = "right"
        elif delta_x < -1:
            self.state.facing = "left"
