from pathlib import Path

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

from .asset_manifest import CharacterAssetManifest

SPRITE_SCALE = 2


class CharacterRenderer:
    def __init__(self, manifest: CharacterAssetManifest) -> None:
        self.manifest = manifest
        self._pose_frames = self._load_pose_frames()
        self._visible_pose_bounds = self._compute_visible_bounds()

    def paint(self, painter: QPainter, pose_id: str, *, frame_index: int = 0) -> None:
        resolved_pose_id = self.resolve_pose_id(pose_id)
        if not resolved_pose_id:
            return

        frames = self._pose_frames[resolved_pose_id]
        frame = frames[frame_index % len(frames)]
        frame_rect = self._target_rect_for_frame(frame)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.drawPixmap(frame_rect, frame)

    def has_frames(self, pose_id: str | None = None) -> bool:
        if pose_id is None:
            return bool(self._pose_frames)
        return bool(self._pose_frames.get(pose_id))

    def frame_count(self, pose_id: str) -> int:
        resolved_pose_id = self.resolve_pose_id(pose_id)
        if not resolved_pose_id:
            return 0
        return len(self._pose_frames[resolved_pose_id])

    def resolve_pose_id(self, pose_id: str) -> str:
        cleaned = str(pose_id or "").strip().lower()
        if cleaned in self._pose_frames:
            return cleaned
        if self.manifest.fallback_pose_id in self._pose_frames:
            return self.manifest.fallback_pose_id
        if self._pose_frames:
            return next(iter(self._pose_frames))
        return ""

    def bubble_anchor(self, pose_id: str) -> tuple[int, int]:
        resolved_pose_id = self.resolve_pose_id(pose_id)
        visible_bounds = self._visible_pose_bounds.get(resolved_pose_id)
        if visible_bounds is None:
            return self.manifest.bounds.bubble_anchor

        headroom = max(24, min(48, visible_bounds.height() // 5))
        return visible_bounds.center().x(), visible_bounds.top() + headroom

    def _load_pose_frames(self) -> dict[str, list[QPixmap]]:
        poses_dir = (
            Path(__file__).resolve().parents[2]
            / "assets"
            / self.manifest.character_id
        )
        if not poses_dir.exists():
            return {}

        pose_frames: dict[str, list[QPixmap]] = {}
        for pose_dir in sorted(path for path in poses_dir.iterdir() if path.is_dir()):
            frames = self._load_frames_from_dir(pose_dir)
            if frames:
                pose_frames[pose_dir.name.lower()] = frames
        return pose_frames

    def _load_frames_from_dir(self, frames_dir: Path) -> list[QPixmap]:
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

    def _compute_visible_bounds(self) -> dict[str, QRect]:
        visible_bounds: dict[str, QRect] = {}
        for pose_id, frames in self._pose_frames.items():
            frame = frames[0]
            frame_rect = self._target_rect_for_frame(frame)
            opaque_rect = self._opaque_bounds(frame.toImage())
            if opaque_rect is None:
                visible_bounds[pose_id] = frame_rect
                continue

            scaled_left = frame_rect.left() + (opaque_rect.left() * SPRITE_SCALE)
            scaled_top = frame_rect.top() + (opaque_rect.top() * SPRITE_SCALE)
            scaled_width = opaque_rect.width() * SPRITE_SCALE
            scaled_height = opaque_rect.height() * SPRITE_SCALE
            visible_bounds[pose_id] = QRect(
                scaled_left,
                scaled_top,
                scaled_width,
                scaled_height,
            )
        return visible_bounds

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
