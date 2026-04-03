from pathlib import Path

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

from .asset_manifest import CharacterAssetManifest
from .presentation_models import CharacterPresentation

SPRITE_SCALE = 2


class CharacterRenderer:
    def __init__(self, manifest: CharacterAssetManifest) -> None:
        self.manifest = manifest
        self._idle_frames = self._load_idle_frames()
        self._visible_idle_bounds = self._compute_visible_bounds()

    def paint(
        self, painter: QPainter, presentation: CharacterPresentation, *, frame_index: int = 0
    ) -> None:
        del presentation
        if not self._idle_frames:
            return

        frame = self._idle_frames[frame_index % len(self._idle_frames)]
        frame_rect = self._target_rect_for_frame(frame)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.drawPixmap(frame_rect, frame)

    def has_frames(self) -> bool:
        return bool(self._idle_frames)

    def frame_count(self) -> int:
        return len(self._idle_frames)

    def bubble_anchor(self) -> tuple[int, int]:
        if self._visible_idle_bounds is None:
            return self.manifest.bounds.bubble_anchor

        headroom = max(24, min(48, self._visible_idle_bounds.height() // 5))
        return self._visible_idle_bounds.center().x(), self._visible_idle_bounds.top() + headroom

    def _load_idle_frames(self) -> list[QPixmap]:
        frames_dir = (
            Path(__file__).resolve().parents[2]
            / "assets"
            / "character"
            / self.manifest.character_id
            / "poses"
            / "idle"
        )
        if not frames_dir.exists():
            return []

        frames: list[QPixmap] = []
        for frame_path in sorted(frames_dir.glob("*.png")):
            pixmap = QPixmap(str(frame_path))
            if not pixmap.isNull():
                frames.append(pixmap)
        return frames

    def _target_rect_for_frame(self, frame: QPixmap) -> QRect:
        scaled_width = frame.width() * SPRITE_SCALE
        scaled_height = frame.height() * SPRITE_SCALE
        feet_x, feet_y = self.manifest.bounds.feet_anchor
        top_left = QPoint(feet_x - scaled_width // 2, feet_y - scaled_height)
        return QRect(top_left.x(), top_left.y(), scaled_width, scaled_height)

    def _compute_visible_bounds(self) -> QRect | None:
        if not self._idle_frames:
            return None

        frame = self._idle_frames[0]
        frame_rect = self._target_rect_for_frame(frame)
        opaque_rect = self._opaque_bounds(frame.toImage())
        if opaque_rect is None:
            return frame_rect

        scaled_left = frame_rect.left() + (opaque_rect.left() * SPRITE_SCALE)
        scaled_top = frame_rect.top() + (opaque_rect.top() * SPRITE_SCALE)
        scaled_width = opaque_rect.width() * SPRITE_SCALE
        scaled_height = opaque_rect.height() * SPRITE_SCALE
        return QRect(scaled_left, scaled_top, scaled_width, scaled_height)

    def _opaque_bounds(self, image: QImage) -> QRect | None:
        min_x = image.width()
        min_y = image.height()
        max_x = -1
        max_y = -1

        for y in range(image.height()):
            for x in range(image.width()):
                if QColor(image.pixel(x, y)).alpha() <= 0:
                    continue
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

        if max_x < min_x or max_y < min_y:
            return None
        return QRect(min_x, min_y, (max_x - min_x) + 1, (max_y - min_y) + 1)
