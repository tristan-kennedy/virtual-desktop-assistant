from __future__ import annotations

import argparse
import re
import subprocess
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
_PRERELEASE_PATTERN = re.compile(r"(?i)(?:a|b|rc|dev)\d*(?:$|[.+-])")
_FILENAME_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def read_pyproject(pyproject_path: Path = PYPROJECT_PATH) -> dict:
    with pyproject_path.open("rb") as file:
        return tomllib.load(file)


def read_project_version(pyproject_path: Path = PYPROJECT_PATH) -> str:
    return str(read_pyproject(pyproject_path)["project"]["version"]).strip()


def parse_project_version(pyproject_text: str) -> str:
    return str(tomllib.loads(pyproject_text)["project"]["version"]).strip()


def read_previous_project_version(ref: str = "HEAD^", repo_root: Path = REPO_ROOT) -> str | None:
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:pyproject.toml"],
            check=True,
            capture_output=True,
            cwd=repo_root,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None

    return parse_project_version(result.stdout)


def is_prerelease_version(version: str) -> bool:
    return bool(_PRERELEASE_PATTERN.search(version.strip()))


def sanitize_for_filename(value: str) -> str:
    sanitized = _FILENAME_SAFE_PATTERN.sub("-", value).strip(".-")
    return sanitized or "artifact"


def build_release_metadata(current_version: str, previous_version: str | None) -> dict[str, str]:
    version_changed = current_version != previous_version
    prerelease = is_prerelease_version(current_version)
    sanitized_version = sanitize_for_filename(current_version)
    installer_base_name = f"DipsyDolphin-Setup-{sanitized_version}"

    return {
        "current_version": current_version,
        "previous_version": previous_version or "",
        "version_changed": str(version_changed).lower(),
        "should_release": str(version_changed).lower(),
        "is_prerelease": str(prerelease).lower(),
        "release_type": "prerelease" if prerelease else "release",
        "tag_name": f"v{current_version}",
        "release_name": f"Dipsy Dolphin {current_version}",
        "installer_base_name": installer_base_name,
        "installer_path": f".artifacts/windows/installer/{installer_base_name}.exe",
    }


def write_github_output(output_path: Path, outputs: dict[str, str]) -> None:
    lines = [f"{key}={value}\n" for key, value in outputs.items()]
    with output_path.open("a", encoding="utf-8") as file:
        file.writelines(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive release metadata from pyproject.toml.")
    parser.add_argument(
        "--github-output", type=Path, help="Path to the GitHub Actions output file."
    )
    parser.add_argument(
        "--ref", default="HEAD^", help="Git ref used to read the previous pyproject.toml."
    )
    args = parser.parse_args(argv)

    current_version = read_project_version()
    previous_version = read_previous_project_version(ref=args.ref)
    outputs = build_release_metadata(current_version, previous_version)

    if args.github_output is not None:
        write_github_output(args.github_output, outputs)
    else:
        for key, value in outputs.items():
            print(f"{key}={value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
