import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from .presentation_models import CharacterBounds


@dataclass(frozen=True)
class CharacterAssetManifest:
    character_id: str
    style_variant: str
    future_style_variant: str
    fallback_draw_mode: str
    bounds: CharacterBounds
    layer_order: Tuple[str, ...]
    supported_states: Dict[str, Tuple[str, ...]]


def load_character_manifest(character_id: str = "dipsy") -> CharacterAssetManifest:
    manifest_path = _repo_root() / "assets" / "character" / character_id / "manifest.json"
    if not manifest_path.exists():
        return _default_manifest(character_id)

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_manifest(character_id)

    anchors = payload.get("anchors", {})
    canvas = payload.get("canvas_size", {})
    supported = payload.get("supported", {})
    return CharacterAssetManifest(
        character_id=str(payload.get("character_id", character_id)),
        style_variant=str(payload.get("style_variant", "flat-retro")),
        future_style_variant=str(payload.get("future_style_variant", "faux-3d")),
        fallback_draw_mode=str(payload.get("fallback_draw_mode", "vector")),
        bounds=CharacterBounds(
            width=int(canvas.get("width", 200)),
            height=int(canvas.get("height", 220)),
            bubble_anchor=_as_point(anchors.get("bubble"), (154, 54)),
            feet_anchor=_as_point(anchors.get("feet"), (104, 194)),
            look_anchor=_as_point(anchors.get("look"), (104, 74)),
        ),
        layer_order=tuple(payload.get("layer_order", _default_manifest(character_id).layer_order)),
        supported_states={
            key: tuple(value) for key, value in supported.items() if isinstance(value, list)
        },
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
        style_variant="flat-retro",
        future_style_variant="faux-3d",
        fallback_draw_mode="vector",
        bounds=CharacterBounds(
            width=200,
            height=220,
            bubble_anchor=(154, 54),
            feet_anchor=(104, 194),
            look_anchor=(104, 74),
        ),
        layer_order=("shadow", "tail", "body", "head", "face", "mouth", "badge", "fx"),
        supported_states={
            "poses": ("idle", "walk", "talk", "think", "laugh", "surprised", "sad", "excited"),
            "expressions": ("neutral", "happy", "concerned"),
            "eye_states": ("open", "blink"),
            "mouth_states": ("closed", "talk_open"),
            "effects": ("question", "spark", "sweat"),
        },
    )
