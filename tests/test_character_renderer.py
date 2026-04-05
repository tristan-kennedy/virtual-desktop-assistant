import os

from PySide6.QtWidgets import QApplication

from dipsy_dolphin.ui.asset_manifest import load_character_manifest
from dipsy_dolphin.ui.character_renderer import CharacterRenderer


def test_renderer_loads_idle_sprite_sequence_from_assets() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    manifest = load_character_manifest()
    renderer = CharacterRenderer(manifest)

    assert app is not None
    assert renderer.has_frames() is True
    assert renderer.frame_count("idle") == 24
    assert renderer.frame_count("talk") == 24


def test_renderer_doubles_sprite_size_from_source_frame() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    manifest = load_character_manifest()
    renderer = CharacterRenderer(manifest)
    frame = renderer._pose_frames["idle"][0]
    rect = renderer._target_rect_for_frame(frame)

    assert app is not None
    assert rect.width() == frame.width() * 2
    assert rect.height() == frame.height() * 2


def test_renderer_bubble_anchor_tracks_visible_sprite_area() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    manifest = load_character_manifest()
    renderer = CharacterRenderer(manifest)
    bubble_x, bubble_y = renderer.bubble_anchor("idle")

    assert app is not None
    assert abs(bubble_x - manifest.bounds.feet_anchor[0]) <= 1
    assert bubble_y > 80
    assert bubble_y < manifest.bounds.feet_anchor[1]
