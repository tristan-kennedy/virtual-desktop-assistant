from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

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
    *, uv_path: str, python_version: str, env: dict[str, str]
) -> None:
    run_command([uv_path, "python", "install", "--no-registry", python_version], env=env)
    run_command(
        [
            uv_path,
            "sync",
            "--project",
            str(REPO_ROOT),
            "--locked",
            "--managed-python",
            "--python",
            python_version,
            "--no-default-groups",
            "--group",
            "packaging",
        ],
        env=env,
    )


def build_app(*, clean: bool, python_version: str | None) -> Path:
    resolved_python_version = resolve_python_version(python_version)
    uv_path = resolve_uv()

    if clean:
        shutil.rmtree(BUILD_VENV, ignore_errors=True)
        shutil.rmtree(PYINSTALLER_ROOT, ignore_errors=True)

    PYINSTALLER_BUILD_PATH.mkdir(parents=True, exist_ok=True)
    PYINSTALLER_DIST_PATH.mkdir(parents=True, exist_ok=True)
    PYINSTALLER_SPEC_PATH.mkdir(parents=True, exist_ok=True)

    env = build_environment(resolved_python_version)
    prepare_packaging_environment(uv_path=uv_path, python_version=resolved_python_version, env=env)
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
            str(LAUNCHER_PATH),
        ],
        env=env,
    )

    print(
        f"Built Dipsy Dolphin app bundle for version {read_project_version()} into {APP_BUNDLE_PATH} using Python {resolved_python_version}."
    )
    return APP_BUNDLE_PATH


def build_installer(
    *,
    clean: bool,
    python_version: str | None,
    skip_app_build: bool,
    app_version: str | None,
    output_base_name: str | None,
) -> Path:
    resolved_app_version = (app_version or read_project_version()).strip()

    if not skip_app_build:
        build_app(clean=clean, python_version=python_version)

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
        build_app(clean=args.clean, python_version=args.python_version)
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
