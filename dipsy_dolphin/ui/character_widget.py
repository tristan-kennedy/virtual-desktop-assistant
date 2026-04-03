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
        self._frame_index = 0

        bounds = self.character_bounds()
        self.setFixedSize(bounds.width, bounds.height)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._advance_frame)
        self.animation_timer.start(100)

    def character_bounds(self) -> CharacterBounds:
        return self.manifest.bounds

    def bubble_anchor(self) -> tuple[int, int]:
        return self.renderer.bubble_anchor()

    def set_presentation(self, presentation: CharacterPresentation) -> None:
        self._base_presentation = presentation
        self.update()

    def _advance_frame(self) -> None:
        if not self.renderer.has_frames():
            return
        self._frame_index = (self._frame_index + 1) % self.renderer.frame_count()
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        # Temporary sprite-only bridge: always play the exported idle loop until
        # pose/emotion-specific sprite routing is implemented.
        self.renderer.paint(painter, self._base_presentation, frame_index=self._frame_index)
