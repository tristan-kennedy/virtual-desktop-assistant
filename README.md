# Dipsy Dolphin

This project is currently on pause. I am not actively expanding it right now, but the repo is being left in a runnable, packaged, release-ready state.

Dipsy Dolphin is a small Windows desktop companion inspired by theatrical retro assistants like BonziBuddy. It is intentionally visible, character-driven, and local-first.

## Current functionality

- Shows a floating always-on-top PySide6 desktop character with sprite-based `idle` and `talk` animation.
- Supports drag-to-move, double-click chat, a speech bubble, and optional retro Windows voice playback.
- Uses a bundled local GGUF model through llama.cpp for chat, startup behavior, and inactivity-driven turns.
- Saves both a local profile and structured memory on Windows.
- Supports bounded desktop actions through chat: browser search, opening `http` or `https` URLs, opening an existing local path, and focusing or opening supported apps.
- Supported built-in app targets are the default browser, Terminal, Explorer, Notepad, and Settings.

## Project layout

- `dipsy_dolphin/ui/` - desktop window, character sprite playback, bubble UI, and presentation handling.
- `dipsy_dolphin/core/` - dialogue coordination, session state, and memory structures.
- `dipsy_dolphin/llm/` - local model/runtime discovery and response generation.
- `dipsy_dolphin/desktop/` and `dipsy_dolphin/actions/` - bounded desktop-control actions and app catalog.
- `dipsy_dolphin/storage/` - local profile and memory persistence.
- `dipsy_dolphin/voice/` - retro voice selection and Windows speech service.
- `assets/dipsy/` - current character sprite assets.
- `scripts/windows_build.py` and `packaging/windows/` - Windows packaging and installer files.

## Run locally

Requires `uv` on Windows. The app supports Python `3.10` through `3.14`, and local development is pinned to Python `3.12` through `.python-version`.

Install `uv` if needed:

```powershell
winget install --id=astral-sh.uv -e
```

Sync the local environment:

```powershell
uv python install
uv sync --group local-llm
```

Download the bundled model and llama.cpp runtime:

```powershell
uv run python -m scripts.windows_build model-bundle
```

Run the app:

```powershell
uv run dipsy-dolphin
```

Local development now requires both the bundled model and the bundled llama.cpp runtime. If you manage the model file manually, place it under `.artifacts/local-models/default/` using the filename declared in `dipsy_dolphin/llm/model_catalog.py`.

If the repo-local `.venv` points at a missing uv-managed interpreter under `AppData\Roaming\uv\python\...`, treat the venv as disposable local state and recreate it:

```powershell
Remove-Item -Recurse -Force .venv
uv python install
uv sync --group local-llm
```

If `uv run ...` fails before startup with an error around `C:\Users\<you>\AppData\Local\uv\cache`, fix that local uv cache path first and then rerun the normal setup commands above. The repo does not attempt to repair user-level uv cache state automatically.

Profile data, including voice settings, is stored in `%LOCALAPPDATA%\DipsyDolphin\data\profile.json` and memory data is stored in `%LOCALAPPDATA%\DipsyDolphin\data\memory.json`.

`uv sync --group local-llm` installs the local dev tooling too, so `uv run pytest` and `uv run ruff check .` are available right away. The actual inference runtime is downloaded by `model-bundle`, not by `uv sync`.

Common dependency commands:

```powershell
uv add <package>
uv remove <package>
uv lock --upgrade-package <package>
```

If another tool still needs a pip-style export, generate it from the lockfile instead of maintaining `requirements.txt` by hand:

```powershell
uv export --format requirements.txt -o requirements.txt
```

## Build Windows installer

Build the standalone Windows app bundle:

```powershell
uv run python -m scripts.windows_build app --clean
```

Download the bundled model payload and llama.cpp runtime for local development:

```powershell
uv run python -m scripts.windows_build model-bundle
```

Build the installer:

```powershell
uv run python -m scripts.windows_build installer --clean
```

The Windows installer is now an online installer: it packages the app itself, then downloads the local model and llama.cpp runtime during setup. This keeps the GitHub release asset to a single installer file.

Windows packaging assets now live under `packaging/windows/assets/`. The current v1 icon is derived from an existing Dipsy sprite and committed as `packaging/windows/assets/app.ico`.

If you prefer Windows-native wrappers, `packaging/windows/build-app.ps1` and `packaging/windows/build-installer.ps1` remain thin shims around the Python tooling.

If Inno Setup is not installed yet, one option is:

```powershell
winget install JRSoftware.InnoSetup
```

The generated outputs stay under `.artifacts/` so the repo root stays clean.

## GitHub releases

Releases come directly from `project.version` in `pyproject.toml` when changes land on `main`.

- If a push to `main` does not change `project.version`, no release is created.
- Stable releases publish normal GitHub releases.
- Installer assets are named from the same version, for example `DipsyDolphin-Setup-1.0.0.exe`.
- Curated release notes are read from `docs/releases/<version>.md`.
- The automated release workflow now runs packaging helper tests, builds the installer, and runs a fast release smoke check before publishing.

Typical flow:

```powershell
uv version 1.0.0
git commit -am "Release 1.0.0"
git push origin main
```

Before changing `project.version`, add a matching release notes file such as `docs/releases/1.0.1.md`.

## Controls

- Drag with left click to move the character.
- Double click Dipsy to open chat.
- Ask through chat when you want Dipsy to do something, including closing the app.
- Press `Esc` to quit.

## Current testing focus

- `tests/test_controller.py` - controller orchestration and guardrails.
- `tests/test_response_parser.py` - structured output sanitization.
- `tests/test_llm_config.py` - local model discovery rules.
- `tests/test_animation_state_machine.py` and `tests/test_presentation_controller.py` - presentation behavior contracts.
- `tests/test_profile_store.py` and `tests/test_brain.py` - persistence and profile parsing helpers.
- `tests/test_voice_retro.py`, `tests/test_voice_service.py`, and `tests/test_windows_speech_backend.py` - retro voice selection and runtime behavior.
