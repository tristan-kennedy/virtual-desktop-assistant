# Dipsy Dolphin

Dipsy Dolphin is a small Windows desktop companion inspired by theatrical retro assistants like BonziBuddy.
It is intentionally visible, character-driven, and local-first: a floating UI talks to a bundled local LLM, turns the model output into structured turns, and keeps the runtime legible as the project grows toward richer assistant capabilities through conversation.

## What the app does

- Shows a floating PySide6 desktop character.
- Supports drag-to-move and quick chat directly with the character.
- Uses a bundled local GGUF model through llama.cpp for startup, onboarding, chat-first requests, and inactivity-driven turns.
- Parses model output into structured turn data including `say`, `dialogue_category`, `animation`, `emotion`, `memory_updates`, and `action` before the UI uses it.
- Plays visible presentation states like idle, walk, think, talk, laugh, surprised, sad, and excited.
- Can speak lines through an optional retro Windows voice service that prefers classic old-school voices and keeps speech interruptible.
- Saves both a local profile and structured memory on Windows so Dipsy remembers identity, preferences, and long-term facts between launches.

## Current runtime assumptions

- The app is currently built around a bundled local model and a single desktop UI host.
- Model output is translated into structured runtime data before presentation or execution.
- The current capability surface is small, but the architecture is intended to expand toward richer assistant actions invoked through chat.
- Core behavior, presentation, and execution plumbing should stay separated as the interface grows.

## Current runtime shape

- `dipsy_dolphin/__main__.py` - console entrypoint for `uv run dipsy-dolphin`.
- `dipsy_dolphin/ui/app.py` - main PySide6 shell, timers, dialogs, movement, and controller task lifecycle.
- `dipsy_dolphin/core/controller.py` - main dialogue and autonomy coordinator; builds prompts, calls the provider, applies runtime rules, and returns structured turns.
- `dipsy_dolphin/core/controller_models.py` - `AssistantTurn`, `ActionRequest`, and `ControllerResult`.
- `dipsy_dolphin/core/brain.py` - profile parsing and session reset helpers for the LLM-driven flow.
- `dipsy_dolphin/core/models.py` and `dipsy_dolphin/core/memory.py` - user/session state and structured memory dataclasses shared across UI and controller.
- `dipsy_dolphin/llm/prompt_builder.py` - system prompt and per-event user payload construction.
- `dipsy_dolphin/llm/response_parser.py` - JSON extraction, validation, and sanitization of model output.
- `dipsy_dolphin/llm/local_provider.py` - bundled llama.cpp runtime management and local generation requests.
- `dipsy_dolphin/llm/config.py`, `dipsy_dolphin/llm/model_catalog.py`, `dipsy_dolphin/llm/runtime_catalog.py` - model/runtime discovery and bundle metadata.
- `dipsy_dolphin/desktop/` - Windows desktop-control backend, app catalog, and bounded app launch/focus/open helpers.
- `dipsy_dolphin/actions/registry.py` - current action registry used to sanitize structured action requests.
- `dipsy_dolphin/ui/presentation_policy.py`, `dipsy_dolphin/ui/presentation_controller.py`, `dipsy_dolphin/ui/animation_state_machine.py`, `dipsy_dolphin/ui/character_widget.py`, and `dipsy_dolphin/ui/character_renderer.py` - semantic presentation mapping, animation state handling, bubble styling, and character drawing.
- `dipsy_dolphin/storage/profile_store.py` and `dipsy_dolphin/storage/memory_store.py` - local profile and memory persistence.
- `dipsy_dolphin/voice/` - retro voice selection, Windows speech backend, and isolated speech service contracts.
- `scripts/windows_build.py` - packaging, model-bundle download, and installer orchestration.
- `packaging/windows/` - Windows packaging shims and Inno Setup assets.
- `docs/` - product, architecture, rendering, and Windows packaging notes.
- `TODO.md` - prioritized roadmap from the current runtime state.

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

If you prefer Windows-native wrappers, `packaging/windows/build-app.ps1` and `packaging/windows/build-installer.ps1` remain thin shims around the Python tooling.

If Inno Setup is not installed yet, one option is:

```powershell
winget install JRSoftware.InnoSetup
```

The generated outputs stay under `.artifacts/` so the repo root stays clean.

## GitHub releases

Releases come directly from `project.version` in `pyproject.toml` when changes land on `main`.

- If a push to `main` does not change `project.version`, no release is created.
- PEP 440 prerelease versions like `0.1.0b1` publish GitHub prereleases.
- Stable versions like `0.1.0` publish normal GitHub releases.
- Installer assets are named from the same version, for example `DipsyDolphin-Setup-0.1.0b1.exe`.

Typical flow:

```powershell
uv version 0.1.0b1
git commit -am "Bump version to 0.1.0b1"
git push origin main
```

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

## Suggested next additions

- Expand beyond the first desktop-control slice into richer assistant capabilities such as reminders, notes, or deeper app integrations.
- Add more theatrical scene behaviors and stronger visible routines.
- Keep improving visual polish, staging, and sprite presentation.
- Add push-to-talk or STT input.
- Harden persistence, migrations, and developer observability.

## AI-friendly workflow

If you are using AI heavily in this repo, read in this order:

1. `README.md`
2. `AGENTS.md`
3. `TODO.md`
4. `docs/architecture.md`
5. `docs/product-brief.md`
6. `docs/rendering-decision.md`
7. `dipsy_dolphin/core/controller.py`
8. `dipsy_dolphin/llm/prompt_builder.py`
9. `dipsy_dolphin/llm/response_parser.py`
10. `dipsy_dolphin/llm/local_provider.py`
11. `dipsy_dolphin/ui/app.py`
12. `dipsy_dolphin/core/brain.py`

That order gets you the product rules, runtime architecture, LLM contract, and UI host before the smaller helper modules.
