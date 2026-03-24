import random
from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from .asset_manifest import CharacterAssetManifest, load_character_manifest
from .character_renderer import CharacterRenderer
from .presentation_models import CharacterBounds, CharacterPresentation


class CharacterWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.manifest: CharacterAssetManifest = load_character_manifest()
        self.renderer = CharacterRenderer(self.manifest)
        self._base_presentation = CharacterPresentation(style_variant=self.manifest.style_variant)
        self._effective_presentation = self._base_presentation
        self._animation_tick = 0
        self._blink_frames_remaining = 0
        self._next_blink_tick = random.randint(10, 18)

        bounds = self.character_bounds()
        self.setFixedSize(bounds.width, bounds.height)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._advance_frame)
        self.animation_timer.start(140)

    def character_bounds(self) -> CharacterBounds:
        return self.manifest.bounds

    def bubble_anchor(self) -> tuple[int, int]:
        return self.manifest.bounds.bubble_anchor

    def set_presentation(self, presentation: CharacterPresentation) -> None:
        self._base_presentation = presentation
        self._effective_presentation = self._compose_presentation()
        self.update()

    def _advance_frame(self) -> None:
        self._animation_tick += 1
        if self._blink_frames_remaining > 0:
            self._blink_frames_remaining -= 1
        elif self._animation_tick >= self._next_blink_tick:
            self._blink_frames_remaining = 1
            self._next_blink_tick = self._animation_tick + random.randint(14, 26)

        self._effective_presentation = self._compose_presentation()
        self.update()

    def _compose_presentation(self) -> CharacterPresentation:
        bob_offset = self._bob_offset_for_pose(self._base_presentation.pose_id)
        mouth_state = self._base_presentation.mouth_state
        if self._base_presentation.pose_id == "talk":
            mouth_state = "talk_open" if self._animation_tick % 2 == 0 else "closed"

        eye_state = self._base_presentation.eye_state
        if self._blink_frames_remaining > 0:
            eye_state = "blink"

        return CharacterPresentation(
            pose_id=self._base_presentation.pose_id,
            expression_id=self._base_presentation.expression_id,
            eye_state=eye_state,
            mouth_state=mouth_state,
            facing=self._base_presentation.facing,
            active_effects=self._base_presentation.active_effects,
            bob_offset=bob_offset,
            style_variant=self._base_presentation.style_variant,
        )

    def _bob_offset_for_pose(self, pose_id: str) -> int:
        patterns = {
            "idle": (0, 1, 0, -1),
            "walk": (0, 3, 0, -2),
            "talk": (0, 1, 0, -1),
            "think": (0, 0, 1, 0, -1),
            "laugh": (0, 2, 1, -1, -2),
            "surprised": (-1, 1, 0, 1),
            "sad": (0, 0, -1, 0),
            "excited": (0, 2, 0, -2),
        }
        pattern = patterns.get(pose_id, (0,))
        return pattern[self._animation_tick % len(pattern)]

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        self.renderer.paint(painter, self._effective_presentation)
