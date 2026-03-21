from dataclasses import dataclass, field
from typing import Optional, Tuple

from .asset_manifest import load_character_manifest
from .presentation_models import CharacterPresentation


@dataclass
class PresentationSceneState:
    movement_pose: str = "idle"
    focus_pose: Optional[str] = None
    speech_style: Optional[str] = None
    facing: str = "right"
    extra_effects: Tuple[str, ...] = field(default_factory=tuple)


class PresentationController:
    def __init__(self) -> None:
        self.manifest = load_character_manifest()
        self.state = PresentationSceneState()

    def set_idle(self, delta_x: float = 0) -> None:
        self.state.movement_pose = "idle"
        self.state.focus_pose = None
        self._set_facing_from_delta(delta_x)

    def set_walking(self, delta_x: float) -> None:
        self.state.movement_pose = "walk"
        self.state.focus_pose = None
        self._set_facing_from_delta(delta_x)

    def set_thinking(self, delta_x: float = 0) -> None:
        self.state.focus_pose = "think"
        self._set_facing_from_delta(delta_x)

    def start_speech(self, style: str = "normal") -> None:
        self.state.speech_style = style
        self.state.focus_pose = None

    def stop_speech(self) -> None:
        self.state.speech_style = None

    def resolve(self) -> CharacterPresentation:
        pose_id = self.state.movement_pose
        if self.state.focus_pose == "think":
            pose_id = "think"
        if self.state.speech_style:
            pose_id = "talk"

        expression_id = "neutral"
        active_effects = list(self.state.extra_effects)

        if self.state.speech_style in {"joke", "spark"}:
            expression_id = "happy"
            active_effects.append("spark")
        elif self.state.speech_style in {"question", "onboarding"}:
            expression_id = "concerned"
            active_effects.append("question")
        elif self.state.speech_style == "alert":
            expression_id = "concerned"
            active_effects.append("sweat")
        elif pose_id == "think":
            expression_id = "concerned"
            active_effects.append("question")
        elif self.state.movement_pose == "walk":
            expression_id = "happy"

        mouth_state = "talk_open" if pose_id == "talk" else "closed"
        return CharacterPresentation(
            pose_id=pose_id,
            expression_id=expression_id,
            eye_state="open",
            mouth_state=mouth_state,
            facing=self.state.facing,
            active_effects=tuple(dict.fromkeys(active_effects)),
            style_variant=self.manifest.style_variant,
        )

    def _set_facing_from_delta(self, delta_x: float) -> None:
        if delta_x > 1:
            self.state.facing = "right"
        elif delta_x < -1:
            self.state.facing = "left"
