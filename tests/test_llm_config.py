from pathlib import Path

from dipsy_dolphin.llm.config import resolve_model_bundle


def test_resolve_model_bundle_prefers_env_model_dir(monkeypatch, tmp_path: Path) -> None:
    model_root = tmp_path / "models"
    model_dir = model_root / "default"
    model_dir.mkdir(parents=True)
    model_path = model_dir / "Qwen3.5-9B-Q4_K_M.gguf"
    model_path.write_text("fake model", encoding="utf-8")

    monkeypatch.setenv("DIPSY_MODEL_DIR", str(model_root))

    resolved = resolve_model_bundle()

    assert resolved is not None
    assert resolved.model_path == model_path
