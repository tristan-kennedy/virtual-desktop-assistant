from typing import Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

from .asset_manifest import CharacterAssetManifest, load_character_manifest
from .character_renderer import CharacterRenderer
from .presentation_models import CharacterBounds, CharacterPresentation


class CharacterWidget(QWidget):
    pose_presented = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.manifest: CharacterAssetManifest = load_character_manifest()
        self.renderer = CharacterRenderer(self.manifest)
        self._base_presentation = CharacterPresentation(style_variant=self.manifest.style_variant)
        self._active_pose_id = self.renderer.resolve_pose_id(self.manifest.fallback_pose_id)
        self._pending_pose_id = self._active_pose_id
        self._presented_pose_id = self._active_pose_id
        self._pose_ready_to_emit = ""
        self._frame_index = 0

        bounds = self.character_bounds()
        self.setFixedSize(bounds.width, bounds.height)

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._advance_frame)
        self.animation_timer.start(100)

    def character_bounds(self) -> CharacterBounds:
        return self.manifest.bounds

    def bubble_anchor(self) -> tuple[int, int]:
        return self.renderer.bubble_anchor(self._active_pose_id)

    def active_pose_id(self) -> str:
        return self._active_pose_id

    def resolve_pose_id(self, pose_id: str) -> str:
        return self.renderer.resolve_pose_id(pose_id)

    def is_pose_active(self, pose_id: str) -> bool:
        resolved_pose_id = self.resolve_pose_id(pose_id)
        return bool(resolved_pose_id) and resolved_pose_id == self._active_pose_id

    def set_presentation(self, presentation: CharacterPresentation) -> None:
        self._base_presentation = presentation
        requested_pose_id = self.renderer.resolve_pose_id(presentation.pose_id)
        self._pending_pose_id = requested_pose_id or self._active_pose_id
        self.update()

    def _advance_frame(self) -> None:
        if not self.renderer.has_frames():
            return

        frame_count = self.renderer.frame_count(self._active_pose_id)
        if frame_count <= 0:
            return

        next_frame_index = self._frame_index + 1
        if next_frame_index >= frame_count:
            if self._pending_pose_id != self._active_pose_id:
                self._active_pose_id = self._pending_pose_id
                self._pose_ready_to_emit = self._active_pose_id
            next_frame_index = 0

        self._frame_index = next_frame_index
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        self.renderer.paint(painter, self._active_pose_id, frame_index=self._frame_index)
        self._presented_pose_id = self._active_pose_id
        if self._pose_ready_to_emit and self._pose_ready_to_emit == self._presented_pose_id:
            pose_id = self._pose_ready_to_emit
            self._pose_ready_to_emit = ""
            self.pose_presented.emit(pose_id)
