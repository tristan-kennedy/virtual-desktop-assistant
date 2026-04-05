from pathlib import Path

import pytest

from scripts import windows_build


def test_parse_windows_version_supports_prerelease_serial() -> None:
    assert windows_build.parse_windows_version("0.1.0b5") == (0, 1, 0, 5)


def test_build_version_file_contents_includes_windows_metadata() -> None:
    contents = windows_build.build_version_file_contents("1.0.0")

    assert "Dipsy Dolphin desktop companion" in contents
    assert "ProductVersion', '1.0.0'" in contents
    assert "filevers=(1, 0, 0, 0)" in contents


def test_resolve_packaging_assets_requires_app_icon(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="app.ico"):
        windows_build.resolve_packaging_assets(tmp_path)


def test_validate_release_artifacts_checks_expected_outputs(tmp_path: Path) -> None:
    packaging_assets_root = tmp_path / "packaging-assets"
    packaging_assets_root.mkdir()
    (packaging_assets_root / "app.ico").write_bytes(b"ico")

    app_bundle_path = tmp_path / "app-bundle"
    app_bundle_path.mkdir()
    (app_bundle_path / "DipsyDolphin.exe").write_bytes(b"exe")

    installer_path = tmp_path / "installer.exe"
    installer_path.write_bytes(b"setup")

    docs_root = tmp_path / "docs" / "releases"
    docs_root.mkdir(parents=True)
    (docs_root / "1.0.0.md").write_text("# Release", encoding="utf-8")

    windows_build.validate_release_artifacts(
        version="1.0.0",
        installer_path=installer_path,
        app_bundle_path=app_bundle_path,
        packaging_assets_root=packaging_assets_root,
        repo_root=tmp_path,
    )


def test_validate_release_artifacts_requires_release_notes(tmp_path: Path) -> None:
    packaging_assets_root = tmp_path / "packaging-assets"
    packaging_assets_root.mkdir()
    (packaging_assets_root / "app.ico").write_bytes(b"ico")

    app_bundle_path = tmp_path / "app-bundle"
    app_bundle_path.mkdir()
    (app_bundle_path / "DipsyDolphin.exe").write_bytes(b"exe")

    installer_path = tmp_path / "installer.exe"
    installer_path.write_bytes(b"setup")

    with pytest.raises(RuntimeError, match="release notes"):
        windows_build.validate_release_artifacts(
            version="1.0.0",
            installer_path=installer_path,
            app_bundle_path=app_bundle_path,
            packaging_assets_root=packaging_assets_root,
            repo_root=tmp_path,
        )
