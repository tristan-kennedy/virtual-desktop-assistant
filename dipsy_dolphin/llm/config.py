import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .model_catalog import DEFAULT_MODEL_BUNDLE, ModelBundle


@dataclass(frozen=True)
class ResolvedModelBundle:
    bundle: ModelBundle
    model_path: Path


def discover_model_bundle() -> ResolvedModelBundle | None:
    direct_path = os.environ.get("DIPSY_MODEL_PATH", "").strip()
    if direct_path:
        candidate = Path(direct_path).resolve(strict=False)
        if candidate.exists():
            return ResolvedModelBundle(bundle=DEFAULT_MODEL_BUNDLE, model_path=candidate)

    for root in _candidate_model_roots(DEFAULT_MODEL_BUNDLE):
        candidates = [
            root / DEFAULT_MODEL_BUNDLE.app_subdir / DEFAULT_MODEL_BUNDLE.filename,
            root / DEFAULT_MODEL_BUNDLE.filename,
        ]
        for candidate in candidates:
            if candidate.exists():
                return ResolvedModelBundle(bundle=DEFAULT_MODEL_BUNDLE, model_path=candidate)
    return None


def resolve_model_bundle() -> ResolvedModelBundle | None:
    return discover_model_bundle()


def _candidate_model_roots(bundle: ModelBundle) -> list[Path]:
    roots: list[Path] = []

    env_dir = os.environ.get("DIPSY_MODEL_DIR", "").strip()
    if env_dir:
        roots.append(Path(env_dir))

    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent / "models")

    package_root = Path(__file__).resolve().parents[2]
    roots.append(package_root / ".artifacts" / "local-models")
    roots.append(package_root / ".artifacts" / "windows" / "model-bundles" / "default" / "models")
    roots.append(package_root / "models")

    seen: set[Path] = set()
    unique_roots: list[Path] = []
    for root in roots:
        resolved_root = root.resolve(strict=False)
        if resolved_root in seen:
            continue
        seen.add(resolved_root)
        unique_roots.append(resolved_root)
    return unique_roots
