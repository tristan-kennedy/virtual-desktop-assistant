# Windows Install

## Overview

Dipsy Dolphin uses a simple two-step Windows packaging flow.

- `scripts.windows_build` is the canonical packaging entrypoint
- `build-app.ps1` and `build-installer.ps1` are thin PowerShell shims for Windows convenience
- `pyproject.toml` and `uv.lock` are the source of truth for dependencies and release versioning
- Profile data is stored in `%LOCALAPPDATA%\DipsyDolphin\data\profile.json`
- The installer registers a normal Windows uninstaller for the current user

## Local build

Build the Windows app bundle with:

```powershell
uv run python -m scripts.windows_build app --clean
```

That command uses `uv` to install the pinned Python version, sync a locked build environment in `.artifacts\windows\.venv-build`, and write the packaged app bundle to `.artifacts\windows\pyinstaller\dist\DipsyDolphin`.

## Installer build

Build the Windows setup wizard with:

```powershell
uv run python -m scripts.windows_build installer --clean
```

Notes:

- The installer build first creates the app bundle unless `--skip-app-build` is supplied
- The app build uses `uv.lock`, so packaging stays reproducible across local and CI runs
- You can override the Python version used for packaging with `--python-version`
- Inno Setup 6 must be installed so `ISCC.exe` is available
- The finished installer is written to `.artifacts\windows\installer\DipsyDolphin-Setup-<version>.exe` by default
- You can override the installer version with `--app-version` and the output file name with `--output-base-name`
- If you prefer PowerShell wrappers, `packaging\windows\build-app.ps1` and `packaging\windows\build-installer.ps1` forward their arguments to the Python CLI

If Inno Setup is not installed yet, one option is:

```powershell
winget install JRSoftware.InnoSetup
```

## Local development

For day-to-day development, let `uv` manage the local project environment:

```powershell
uv python install
uv sync
```

Then run:

```powershell
uv run dipsy-dolphin
```

Common dependency commands:

```powershell
uv add <package>
uv remove <package>
uv lock --upgrade-package <package>
```

If you need a pip-compatible export for some other tool, generate it from the lockfile:

```powershell
uv export --format requirements.txt -o requirements.txt
```

Only use the packaging commands when you want a bundled app or installer. They create and manage a separate locked build environment under `.artifacts\windows\.venv-build`.

## GitHub Actions automation

One workflow now lives in `.github/workflows/versioned-release.yml`.

- Pushes to `main` only create a release when `project.version` changes in `pyproject.toml`
- PEP 440 prerelease versions like `0.3.0b1` or `0.3.0rc1` publish GitHub prereleases
- Stable versions like `0.3.0` publish normal GitHub releases
- The generated installer asset is named from that same version, such as `DipsyDolphin-Setup-0.3.0b1.exe`
