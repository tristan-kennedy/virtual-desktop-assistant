from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from dipsy_dolphin.llm.model_catalog import DEFAULT_MODEL_BUNDLE
from dipsy_dolphin.llm.runtime_catalog import DEFAULT_RUNTIME_BUNDLE

from .versioning import REPO_ROOT, read_project_version, sanitize_for_filename


PACKAGING_ROOT = REPO_ROOT / "packaging" / "windows"
ARTIFACTS_ROOT = REPO_ROOT / ".artifacts" / "windows"
BUILD_VENV = ARTIFACTS_ROOT / ".venv-build"
PYINSTALLER_ROOT = ARTIFACTS_ROOT / "pyinstaller"
PYINSTALLER_BUILD_PATH = PYINSTALLER_ROOT / "build"
PYINSTALLER_DIST_PATH = PYINSTALLER_ROOT / "dist"
PYINSTALLER_SPEC_PATH = PYINSTALLER_ROOT / "spec"
APP_BUNDLE_PATH = PYINSTALLER_DIST_PATH / "DipsyDolphin"
INSTALLER_OUT_DIR = ARTIFACTS_ROOT / "installer"
MODEL_BUNDLES_ROOT = ARTIFACTS_ROOT / "model-bundles"
RUNTIME_BUNDLE_ROOT = ARTIFACTS_ROOT / "llama-runtime"
LAUNCHER_PATH = PACKAGING_ROOT / "launcher.py"
INSTALLER_SCRIPT = PACKAGING_ROOT / "dipsy-dolphin.iss"
PYTHON_VERSION_FILE = REPO_ROOT / ".python-version"


def run_command(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f"> {subprocess.list2cmdline(command)}")
    subprocess.run(command, check=True, cwd=REPO_ROOT, env=env)


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

    if clean:
        shutil.rmtree(BUILD_VENV, ignore_errors=True)
        shutil.rmtree(PYINSTALLER_ROOT, ignore_errors=True)

    PYINSTALLER_BUILD_PATH.mkdir(parents=True, exist_ok=True)
    PYINSTALLER_DIST_PATH.mkdir(parents=True, exist_ok=True)
    PYINSTALLER_SPEC_PATH.mkdir(parents=True, exist_ok=True)

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


def build_model_bundle(*, clean: bool, python_version: str | None) -> Path:
    resolved_python_version = resolve_python_version(python_version)
    uv_path = resolve_uv()
    bundle = DEFAULT_MODEL_BUNDLE
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
    _download_runtime_bundle(clean=clean)
    return bundle_root


def ensure_model_bundle(*, clean: bool, python_version: str | None) -> Path:
    bundle = DEFAULT_MODEL_BUNDLE
    bundle_root = MODEL_BUNDLES_ROOT / "default"
    model_source_dir = bundle_root / "models"
    runtime_source_dir = RUNTIME_BUNDLE_ROOT

    if model_source_dir.exists() and runtime_source_dir.exists():
        return bundle_root

    print(
        f"Preparing bundled model payload for installer because '{bundle.display_name}' is not fully present yet."
    )
    return build_model_bundle(clean=clean, python_version=python_version)


def _download_runtime_bundle(*, clean: bool) -> Path:
    runtime_root = RUNTIME_BUNDLE_ROOT
    downloads_dir = runtime_root / "downloads"
    runtime_zip = downloads_dir / Path(DEFAULT_RUNTIME_BUNDLE.runtime_url).name
    cuda_zip = downloads_dir / Path(DEFAULT_RUNTIME_BUNDLE.cuda_url).name

    if clean:
        shutil.rmtree(runtime_root, ignore_errors=True)

    downloads_dir.mkdir(parents=True, exist_ok=True)
    _download_file(DEFAULT_RUNTIME_BUNDLE.runtime_url, runtime_zip)
    _download_file(DEFAULT_RUNTIME_BUNDLE.cuda_url, cuda_zip)
    _extract_zip(runtime_zip, runtime_root)
    _extract_zip(cuda_zip, runtime_root)
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
    skip_app_build: bool,
    app_version: str | None,
    output_base_name: str | None,
) -> Path:
    resolved_app_version = (app_version or read_project_version()).strip()
    bundle = DEFAULT_MODEL_BUNDLE
    bundle_root = MODEL_BUNDLES_ROOT / "default"
    model_source_dir = bundle_root / "models"
    runtime_source_dir = RUNTIME_BUNDLE_ROOT

    if not skip_app_build:
        build_app(clean=clean, python_version=python_version, include_llm_runtime=True)

    if not APP_BUNDLE_PATH.exists():
        raise RuntimeError(f"App bundle not found at {APP_BUNDLE_PATH}")

    ensure_model_bundle(clean=clean, python_version=python_version)

    if not model_source_dir.exists():
        raise RuntimeError(
            f"Model bundle for '{bundle.display_name}' was expected at {model_source_dir}, but it is still missing after preparation."
        )

    if not runtime_source_dir.exists():
        raise RuntimeError(
            f"Bundled llama.cpp runtime was expected at {runtime_source_dir}, but it is still missing after preparation."
        )

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
            f"/DModelSourceDir={model_source_dir}",
            f"/DRuntimeSourceDir={runtime_source_dir}",
            f"/DOutputDir={INSTALLER_OUT_DIR}",
            f"/DAppVersion={resolved_app_version}",
            f"/DModelDisplayName={bundle.display_name}",
            f"/DOutputBaseName={resolved_output_base_name}",
            str(INSTALLER_SCRIPT),
        ]
    )

    setup_exe = INSTALLER_OUT_DIR / f"{resolved_output_base_name}.exe"
    print(f"Built Windows installer {setup_exe} for version {resolved_app_version}.")
    return setup_exe


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
        build_model_bundle(clean=args.clean, python_version=args.python_version)
        return 0

    build_installer(
        clean=args.clean,
        python_version=args.python_version,
        skip_app_build=args.skip_app_build,
        app_version=args.app_version,
        output_base_name=args.output_base_name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
