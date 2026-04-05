import json
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from .presentation_models import CharacterBounds


@dataclass(frozen=True)
class CharacterAssetManifest:
    character_id: str
    style_variant: str
    fallback_pose_id: str
    speech_pose_id: str
    bounds: CharacterBounds
    supported_poses: Tuple[str, ...]


def load_character_manifest(character_id: str = "dipsy") -> CharacterAssetManifest:
    manifest_path = _repo_root() / "assets" / character_id / "manifest.json"
    if not manifest_path.exists():
        return _default_manifest(character_id)

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_manifest(character_id)

    anchors = payload.get("anchors", {})
    canvas = payload.get("canvas_size", {})
    poses = payload.get("poses")
    if not isinstance(poses, list):
        supported = payload.get("supported", {})
        poses = supported.get("poses", [])
    return CharacterAssetManifest(
        character_id=str(payload.get("character_id", character_id)),
        style_variant=str(payload.get("style_variant", "rendered-sprite")),
        fallback_pose_id=str(payload.get("fallback_pose_id", "idle")).strip() or "idle",
        speech_pose_id=str(payload.get("speech_pose_id", "talk")).strip() or "talk",
        bounds=CharacterBounds(
            width=int(canvas.get("width", 200)),
            height=int(canvas.get("height", 220)),
            bubble_anchor=_as_point(anchors.get("bubble"), (104, 40)),
            feet_anchor=_as_point(anchors.get("feet"), (104, 194)),
            look_anchor=_as_point(anchors.get("look"), (104, 74)),
        ),
        supported_poses=tuple(str(value).strip() for value in poses if str(value).strip()),
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _as_point(value: object, fallback: Tuple[int, int]) -> Tuple[int, int]:
    if isinstance(value, list) and len(value) == 2:
        try:
            return int(value[0]), int(value[1])
        except (TypeError, ValueError):
            return fallback
    return fallback


def _default_manifest(character_id: str) -> CharacterAssetManifest:
    return CharacterAssetManifest(
        character_id=character_id,
        style_variant="rendered-sprite",
        fallback_pose_id="idle",
        speech_pose_id="talk",
        bounds=CharacterBounds(
            width=200,
            height=220,
            bubble_anchor=(104, 40),
            feet_anchor=(104, 194),
            look_anchor=(104, 74),
        ),
        supported_poses=("idle", "talk"),
    )
