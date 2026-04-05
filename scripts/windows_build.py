from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from dipsy_dolphin.llm.model_catalog import DEFAULT_MODEL_BUNDLE
from dipsy_dolphin.llm.runtime_catalog import select_runtime_bundle

from .versioning import (
    REPO_ROOT,
    read_project_version,
    release_notes_path_for_version,
    sanitize_for_filename,
)


PACKAGING_ROOT = REPO_ROOT / "packaging" / "windows"
PACKAGING_ASSETS_ROOT = PACKAGING_ROOT / "assets"
ARTIFACTS_ROOT = REPO_ROOT / ".artifacts" / "windows"
BUILD_VENV = ARTIFACTS_ROOT / ".venv-build"
PYINSTALLER_ROOT = ARTIFACTS_ROOT / "pyinstaller"
PYINSTALLER_BUILD_PATH = PYINSTALLER_ROOT / "build"
PYINSTALLER_DIST_PATH = PYINSTALLER_ROOT / "dist"
PYINSTALLER_SPEC_PATH = PYINSTALLER_ROOT / "spec"
APP_BUNDLE_PATH = PYINSTALLER_DIST_PATH / "DipsyDolphin"
VERSION_INFO_PATH = PYINSTALLER_ROOT / "DipsyDolphin.version-info.txt"
INSTALLER_OUT_DIR = ARTIFACTS_ROOT / "installer"
MODEL_BUNDLES_ROOT = ARTIFACTS_ROOT / "model-bundles"
RUNTIME_BUNDLE_ROOT = ARTIFACTS_ROOT / "llama-runtime"
LAUNCHER_PATH = PACKAGING_ROOT / "launcher.py"
INSTALLER_SCRIPT = PACKAGING_ROOT / "dipsy-dolphin.iss"
PYTHON_VERSION_FILE = REPO_ROOT / ".python-version"
APP_NAME = "Dipsy Dolphin"
APP_EXE_NAME = "DipsyDolphin.exe"
APP_PUBLISHER = "Dipsy Dolphin Project"
APP_FILE_DESCRIPTION = "Dipsy Dolphin desktop companion"
INSTALLER_DESCRIPTION = "Dipsy Dolphin Windows installer"
_WINDOWS_VERSION_PATTERN = re.compile(
    r"^\s*(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:(?:a|b|rc|dev)(?P<serial>\d+))?"
)


@dataclasses.dataclass(frozen=True)
class PackagingAssets:
    app_icon_path: Path
    wizard_image_path: Path | None = None
    wizard_small_image_path: Path | None = None


def run_command(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f"> {subprocess.list2cmdline(command)}")
    subprocess.run(command, check=True, cwd=REPO_ROOT, env=env)


def resolve_packaging_assets(packaging_assets_root: Path = PACKAGING_ASSETS_ROOT) -> PackagingAssets:
    app_icon_path = packaging_assets_root / "app.ico"
    if not app_icon_path.exists():
        raise RuntimeError(
            f"Windows app icon is missing at {app_icon_path}. "
            "Add packaging/windows/assets/app.ico before packaging."
        )

    wizard_image_path = packaging_assets_root / "wizard-image.bmp"
    wizard_small_image_path = packaging_assets_root / "wizard-small.bmp"
    return PackagingAssets(
        app_icon_path=app_icon_path,
        wizard_image_path=wizard_image_path if wizard_image_path.exists() else None,
        wizard_small_image_path=(
            wizard_small_image_path if wizard_small_image_path.exists() else None
        ),
    )


def parse_windows_version(version: str) -> tuple[int, int, int, int]:
    match = _WINDOWS_VERSION_PATTERN.match(version.strip())
    if match is None:
        raise ValueError(f"Unsupported Windows version format: {version!r}")

    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        int(match.group("serial") or "0"),
    )


def build_version_file_contents(
    version: str,
    *,
    product_name: str = APP_NAME,
    file_description: str = APP_FILE_DESCRIPTION,
    publisher: str = APP_PUBLISHER,
    executable_name: str = APP_EXE_NAME,
) -> str:
    file_version = parse_windows_version(version)
    file_version_string = ".".join(str(part) for part in file_version)
    string_values = [
        ("CompanyName", publisher),
        ("FileDescription", file_description),
        ("FileVersion", file_version_string),
        ("InternalName", executable_name),
        ("OriginalFilename", executable_name),
        ("ProductName", product_name),
        ("ProductVersion", version),
    ]
    string_table = ",\n".join(
        f"        StringStruct('{key}', '{value}')" for key, value in string_values
    )
    return (
        "VSVersionInfo(\n"
        f"  ffi=FixedFileInfo(filevers={file_version}, prodvers={file_version},\n"
        "    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)\n"
        "    ),\n"
        "  kids=[\n"
        "    StringFileInfo([\n"
        "      StringTable(\n"
        "        '040904B0',\n"
        "        [\n"
        f"{string_table}\n"
        "        ]\n"
        "      )\n"
        "    ]),\n"
        "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
        "  ]\n"
        ")\n"
    )


def write_version_file(version: str, destination: Path = VERSION_INFO_PATH) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_version_file_contents(version), encoding="utf-8")
    return destination


def expected_installer_path(
    version: str, installer_out_dir: Path = INSTALLER_OUT_DIR
) -> Path:
    installer_base_name = f"DipsyDolphin-Setup-{sanitize_for_filename(version)}"
    return installer_out_dir / f"{installer_base_name}.exe"


def validate_release_artifacts(
    *,
    version: str,
    installer_path: Path | None = None,
    app_bundle_path: Path = APP_BUNDLE_PATH,
    packaging_assets_root: Path = PACKAGING_ASSETS_ROOT,
    repo_root: Path = REPO_ROOT,
) -> None:
    assets = resolve_packaging_assets(packaging_assets_root)
    app_executable = app_bundle_path / APP_EXE_NAME
    if not app_executable.exists():
        raise RuntimeError(f"Expected packaged app executable at {app_executable}")

    resolved_installer_path = installer_path or expected_installer_path(version)
    if not resolved_installer_path.exists():
        raise RuntimeError(f"Expected installer output at {resolved_installer_path}")

    release_notes_path = release_notes_path_for_version(version, repo_root / "docs" / "releases")
    if not release_notes_path.exists():
        raise RuntimeError(f"Expected release notes file at {release_notes_path}")

    if assets.wizard_image_path is not None and not assets.wizard_image_path.exists():
        raise RuntimeError(f"Configured wizard image is missing at {assets.wizard_image_path}")

    if assets.wizard_small_image_path is not None and not assets.wizard_small_image_path.exists():
        raise RuntimeError(
            f"Configured small wizard image is missing at {assets.wizard_small_image_path}"
        )


def resolve_uv() -> str:
    uv_path = shutil.which("uv")
    if uv_path is None:
        raise RuntimeError(
            "uv is required to build Dipsy Dolphin. Install it with 'winget install --id=astral-sh.uv -e'."
        )
    return uv_path


def resolve_python_version(requested_version: str | None) -> str:
    if requested_version:
        return requested_version.strip()

    if PYTHON_VERSION_FILE.exists():
        return PYTHON_VERSION_FILE.read_text(encoding="utf-8").strip()

    return "3.12"


def resolve_iscc() -> str:
    iscc_path = shutil.which("iscc")
    if iscc_path is not None:
        return iscc_path

    possible_paths = [
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
    ]

    for candidate in possible_paths:
        if candidate.exists():
            return str(candidate)

    raise RuntimeError(
        "Inno Setup 6 was not found. Install it with 'winget install JRSoftware.InnoSetup'."
    )


def build_environment(python_version: str) -> dict[str, str]:
    env = os.environ.copy()
    env["UV_PROJECT_ENVIRONMENT"] = str(BUILD_VENV)
    return env


def prepare_packaging_environment(
    *, uv_path: str, python_version: str, env: dict[str, str], groups: list[str]
) -> None:
    run_command([uv_path, "python", "install", "--no-registry", python_version], env=env)
    sync_command = [
        uv_path,
        "sync",
        "--project",
        str(REPO_ROOT),
        "--locked",
        "--managed-python",
        "--python",
        python_version,
        "--no-default-groups",
    ]
    for group in groups:
        sync_command.extend(["--group", group])
    run_command(
        sync_command,
        env=env,
    )


def build_app(
    *, clean: bool, python_version: str | None, include_llm_runtime: bool = False
) -> Path:
    resolved_python_version = resolve_python_version(python_version)
    uv_path = resolve_uv()
    assets = resolve_packaging_assets()

    if clean:
        shutil.rmtree(BUILD_VENV, ignore_errors=True)
        shutil.rmtree(PYINSTALLER_ROOT, ignore_errors=True)

    PYINSTALLER_BUILD_PATH.mkdir(parents=True, exist_ok=True)
    PYINSTALLER_DIST_PATH.mkdir(parents=True, exist_ok=True)
    PYINSTALLER_SPEC_PATH.mkdir(parents=True, exist_ok=True)
    version_info_path = write_version_file(read_project_version())

    env = build_environment(resolved_python_version)
    packaging_groups = ["packaging"]
    if include_llm_runtime:
        packaging_groups.append("local-llm")
    prepare_packaging_environment(
        uv_path=uv_path,
        python_version=resolved_python_version,
        env=env,
        groups=packaging_groups,
    )

    pyinstaller_command = [
        uv_path,
        "run",
        "--project",
        str(REPO_ROOT),
        "--locked",
        "--no-sync",
        "--managed-python",
        "--python",
        resolved_python_version,
        "--no-default-groups",
    ]
    for group in packaging_groups:
        pyinstaller_command.extend(["--group", group])
    pyinstaller_command.extend(
        [
            "python",
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--windowed",
            "--onedir",
            "--name",
            "DipsyDolphin",
            "--icon",
            str(assets.app_icon_path),
            "--version-file",
            str(version_info_path),
            "--specpath",
            str(PYINSTALLER_SPEC_PATH),
            "--distpath",
            str(PYINSTALLER_DIST_PATH),
            "--workpath",
            str(PYINSTALLER_BUILD_PATH),
        ]
    )
    pyinstaller_command.append(str(LAUNCHER_PATH))
    run_command(pyinstaller_command, env=env)

    print(
        f"Built Dipsy Dolphin app bundle for version {read_project_version()} into {APP_BUNDLE_PATH} using Python {resolved_python_version}."
    )
    return APP_BUNDLE_PATH


def build_model_bundle(
    *, clean: bool, python_version: str | None, runtime_backend: str | None = None
) -> Path:
    resolved_python_version = resolve_python_version(python_version)
    uv_path = resolve_uv()
    bundle = DEFAULT_MODEL_BUNDLE
    runtime_bundle = select_runtime_bundle(runtime_backend)
    bundle_root = MODEL_BUNDLES_ROOT / "default"
    models_root = bundle_root / "models" / bundle.app_subdir

    if clean:
        shutil.rmtree(bundle_root, ignore_errors=True)

    models_root.mkdir(parents=True, exist_ok=True)

    env = build_environment(resolved_python_version)
    prepare_packaging_environment(
        uv_path=uv_path,
        python_version=resolved_python_version,
        env=env,
        groups=["packaging", "local-llm"],
    )
    run_command(
        [
            uv_path,
            "run",
            "--project",
            str(REPO_ROOT),
            "--locked",
            "--no-sync",
            "--managed-python",
            "--python",
            resolved_python_version,
            "--no-default-groups",
            "--group",
            "packaging",
            "--group",
            "local-llm",
            "python",
            "-c",
            (
                "from huggingface_hub import hf_hub_download;"
                f"hf_hub_download(repo_id={bundle.repo_id!r}, filename={bundle.filename!r}, local_dir={str(models_root)!r})"
            ),
        ],
        env=env,
    )

    manifest = {
        "model": bundle.display_name,
        "display_name": bundle.display_name,
        "repo_id": bundle.repo_id,
        "filename": bundle.filename,
        "description": bundle.description,
    }
    (bundle_root / "bundle-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    _download_runtime_bundle(runtime_bundle, clean=clean)
    return bundle_root


def ensure_model_bundle(
    *, clean: bool, python_version: str | None, runtime_backend: str | None = None
) -> Path:
    bundle = DEFAULT_MODEL_BUNDLE
    runtime_bundle = select_runtime_bundle(runtime_backend)
    bundle_root = MODEL_BUNDLES_ROOT / "default"
    model_source_dir = bundle_root / "models"
    runtime_source_dir = RUNTIME_BUNDLE_ROOT / runtime_bundle.runtime_id

    if model_source_dir.exists() and runtime_source_dir.exists():
        return bundle_root

    print(
        f"Preparing bundled model payload for installer because '{bundle.display_name}' is not fully present yet."
    )
    return build_model_bundle(
        clean=clean,
        python_version=python_version,
        runtime_backend=runtime_backend,
    )


def _download_runtime_bundle(runtime_bundle, *, clean: bool) -> Path:
    runtime_root = RUNTIME_BUNDLE_ROOT / runtime_bundle.runtime_id
    downloads_dir = runtime_root / "downloads"
    runtime_zip = downloads_dir / Path(runtime_bundle.primary_archive.url).name

    if clean:
        shutil.rmtree(runtime_root, ignore_errors=True)

    downloads_dir.mkdir(parents=True, exist_ok=True)
    _download_file(runtime_bundle.primary_archive.url, runtime_zip)
    _extract_zip(runtime_zip, runtime_root)
    if runtime_bundle.support_archive is not None:
        support_zip = downloads_dir / Path(runtime_bundle.support_archive.url).name
        _download_file(runtime_bundle.support_archive.url, support_zip)
        _extract_zip(support_zip, runtime_root)
    (runtime_root / "runtime-manifest.json").write_text(
        json.dumps(
            {
                "runtime_id": runtime_bundle.runtime_id,
                "display_name": runtime_bundle.display_name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return runtime_root


def _download_file(url: str, destination: Path) -> None:
    if destination.exists():
        return
    print(f"Downloading {url} -> {destination}")
    urllib.request.urlretrieve(url, destination)


def _extract_zip(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination)


def build_installer(
    *,
    clean: bool,
    python_version: str | None,
    runtime_backend: str | None,
    skip_app_build: bool,
    app_version: str | None,
    output_base_name: str | None,
) -> Path:
    resolved_app_version = (app_version or read_project_version()).strip()
    bundle = DEFAULT_MODEL_BUNDLE
    runtime_bundle = select_runtime_bundle(runtime_backend)
    assets = resolve_packaging_assets()

    if not skip_app_build:
        build_app(clean=clean, python_version=python_version, include_llm_runtime=False)

    if not APP_BUNDLE_PATH.exists():
        raise RuntimeError(f"App bundle not found at {APP_BUNDLE_PATH}")

    if clean:
        shutil.rmtree(INSTALLER_OUT_DIR, ignore_errors=True)

    INSTALLER_OUT_DIR.mkdir(parents=True, exist_ok=True)

    resolved_output_base_name = (
        output_base_name or f"DipsyDolphin-Setup-{sanitize_for_filename(resolved_app_version)}"
    )
    iscc_path = resolve_iscc()
    run_command(
        [
            iscc_path,
            f"/DSourceDir={APP_BUNDLE_PATH}",
            f"/DOutputDir={INSTALLER_OUT_DIR}",
            f"/DAppVersion={resolved_app_version}",
            f"/DModelDisplayName={bundle.display_name}",
            f"/DModelDownloadUrl={bundle.download_url}",
            f"/DModelFilename={bundle.filename}",
            f"/DModelInstallSubdir={bundle.app_subdir}",
            f"/DModelSizeBytes={bundle.size_bytes}",
            f"/DModelSha256={bundle.sha256}",
            f"/DRuntimeDownloadUrl={runtime_bundle.primary_archive.url}",
            f"/DRuntimeArchiveName={_url_filename(runtime_bundle.primary_archive.url)}",
            f"/DRuntimeExtractedSize={runtime_bundle.primary_archive.extracted_size}",
            f"/DRuntimeArchiveSha256={runtime_bundle.primary_archive.archive_sha256}",
            (
                f"/DRuntimeSupportDownloadUrl={runtime_bundle.support_archive.url}"
                if runtime_bundle.support_archive is not None
                else "/DRuntimeSupportDownloadUrl="
            ),
            (
                f"/DRuntimeSupportArchiveName={_url_filename(runtime_bundle.support_archive.url)}"
                if runtime_bundle.support_archive is not None
                else "/DRuntimeSupportArchiveName="
            ),
            (
                f"/DRuntimeSupportExtractedSize={runtime_bundle.support_archive.extracted_size}"
                if runtime_bundle.support_archive is not None
                else "/DRuntimeSupportExtractedSize=0"
            ),
            (
                f"/DRuntimeSupportArchiveSha256={runtime_bundle.support_archive.archive_sha256}"
                if runtime_bundle.support_archive is not None
                else "/DRuntimeSupportArchiveSha256="
            ),
            f"/DAppPublisher={APP_PUBLISHER}",
            f"/DAppIconFile={assets.app_icon_path}",
            (
                f"/DWizardImageFile={assets.wizard_image_path}"
                if assets.wizard_image_path is not None
                else "/DWizardImageFile="
            ),
            (
                f"/DWizardSmallImageFile={assets.wizard_small_image_path}"
                if assets.wizard_small_image_path is not None
                else "/DWizardSmallImageFile="
            ),
            f"/DInstallerDescription={INSTALLER_DESCRIPTION}",
            f"/DOutputBaseName={resolved_output_base_name}",
            str(INSTALLER_SCRIPT),
        ]
    )

    setup_exe = INSTALLER_OUT_DIR / f"{resolved_output_base_name}.exe"
    print(f"Built Windows installer {setup_exe} for version {resolved_app_version}.")
    return setup_exe


def _url_filename(url: str) -> str:
    return Path(urlparse(url).path).name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Windows packaging helpers for Dipsy Dolphin.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    app_parser = subparsers.add_parser("app", help="Build the standalone PyInstaller app bundle.")
    app_parser.add_argument(
        "--clean", action="store_true", help="Recreate the isolated packaging environment."
    )
    app_parser.add_argument("--python-version", help="Python version to use for packaging.")
    app_parser.add_argument(
        "--include-llm-runtime",
        action="store_true",
        help="Include the bundled local LLM runtime in the PyInstaller app build.",
    )

    model_parser = subparsers.add_parser(
        "model-bundle", help="Download the bundled GGUF model and llama.cpp runtime."
    )
    model_parser.add_argument("--python-version", help="Python version to use for packaging.")
    model_parser.add_argument(
        "--clean", action="store_true", help="Recreate the model bundle output before downloading."
    )
    model_parser.add_argument(
        "--runtime-backend",
        choices=["auto", "cuda", "vulkan"],
        default="auto",
        help="Choose the bundled llama.cpp runtime backend.",
    )

    installer_parser = subparsers.add_parser("installer", help="Build the Windows installer.")
    installer_parser.add_argument(
        "--clean", action="store_true", help="Recreate packaging outputs before building."
    )
    installer_parser.add_argument("--python-version", help="Python version to use for packaging.")
    installer_parser.add_argument(
        "--skip-app-build", action="store_true", help="Reuse the existing app bundle."
    )
    installer_parser.add_argument(
        "--app-version", help="Override the app version instead of reading pyproject.toml."
    )
    installer_parser.add_argument(
        "--output-base-name", help="Override the generated installer file name."
    )
    installer_parser.add_argument(
        "--runtime-backend",
        choices=["auto", "cuda", "vulkan"],
        default="auto",
        help="Choose the bundled llama.cpp runtime backend.",
    )

    smoke_parser = subparsers.add_parser(
        "release-smoke",
        help="Validate packaging and release artifacts expected by the automated release workflow.",
    )
    smoke_parser.add_argument(
        "--app-version",
        help="Release version to validate. Defaults to project.version in pyproject.toml.",
    )
    smoke_parser.add_argument(
        "--installer-path",
        type=Path,
        help="Explicit installer path to validate instead of the default version-derived path.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "app":
        build_app(
            clean=args.clean,
            python_version=args.python_version,
            include_llm_runtime=args.include_llm_runtime,
        )
        return 0

    if args.command == "model-bundle":
        build_model_bundle(
            clean=args.clean,
            python_version=args.python_version,
            runtime_backend=args.runtime_backend,
        )
        return 0

    if args.command == "release-smoke":
        validate_release_artifacts(
            version=(args.app_version or read_project_version()).strip(),
            installer_path=args.installer_path,
        )
        print("Release smoke validation passed.")
        return 0

    build_installer(
        clean=args.clean,
        python_version=args.python_version,
        runtime_backend=args.runtime_backend,
        skip_app_build=args.skip_app_build,
        app_version=args.app_version,
        output_base_name=args.output_base_name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
