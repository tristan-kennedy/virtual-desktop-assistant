from pathlib import Path

from scripts.versioning import build_release_metadata, release_notes_path_for_version


def test_build_release_metadata_includes_curated_release_notes_path() -> None:
    metadata = build_release_metadata("0.1.0b5", "0.1.0b4")

    assert metadata["release_notes_path"] == "docs/releases/0.1.0b5.md"


def test_release_notes_path_for_version_sanitizes_version_string(tmp_path: Path) -> None:
    path = release_notes_path_for_version("1.0.0 rc1", tmp_path)

    assert path == tmp_path / "1.0.0-rc1.md"
