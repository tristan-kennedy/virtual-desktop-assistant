# Dipsy Dolphin

Dipsy Dolphin is a small Windows desktop pet inspired by old-school assistant apps like BonziBuddy.
The goal is a playful AI-powered virtual assistant with chunky retro graphics, a speech bubble, a robotic voice style, and room to grow into richer desktop-helper behaviors over time.

The current build stays local and visible. It does not perform real malicious actions or silently take over system privileges.

## What the app does

- Shows a floating PySide6 desktop character.
- Supports drag-to-move, right-click actions, and quick chat.
- Uses a speech bubble for assistant replies and character flavor.
- Starts by learning your name and interests, then remembers them on later launches.
- Idles on its own with jokes, doodles, questions, and interest-based chatter.
- Saves your profile locally on Windows so Dipsy can remember you between launches.

## Safety boundaries

- No privilege escalation.
- No registry edits.
- No startup persistence changes.
- No process, file, or network manipulation.
- No hidden execution or destructive behavior.

## Why this project exists

The project is being reshaped into a character-driven desktop companion named Dipsy Dolphin.
Near-term work should focus on personality, retro presentation, AI-backed conversation, and explicit on-screen interactions rather than hidden system behavior.

## Current structure

- `src/dipsy_dolphin/` - installable application package.
- `src/dipsy_dolphin/ui/app.py` - PySide6 window, animation, menus, and speech bubble behavior.
- `src/dipsy_dolphin/core/brain.py` - scripted conversation, onboarding prompts, and autonomous chatter.
- `src/dipsy_dolphin/core/models.py` and `src/dipsy_dolphin/storage/profile_store.py` - profile/session data and local persistence.
- `src/dipsy_dolphin/audio/`, `src/dipsy_dolphin/llm/`, and `src/dipsy_dolphin/actions/` - reserved runtime packages for future expansion.
- `scripts/` - repo-local Python tooling for packaging and release metadata.
- `packaging/windows/` - Windows packaging shims, PyInstaller launcher, and the Inno Setup definition.
- `.github/workflows/` - version-driven Windows release automation.
- `docs/` - product, architecture, rendering, and Windows packaging documentation.
- `TODO.md` - temporary prioritized roadmap for future work.
- `main.py` - compatibility shim that still launches the app directly.
- `pyproject.toml` - project metadata, entrypoints, dependencies, tooling, and release version.
- `uv.lock` - locked dependency graph for repeatable installs and builds.
- `.python-version` - pinned local and CI Python version for `uv`.
- `AGENTS.md` - repo guardrails for AI contributors.

## Run locally

Requires `uv` on Windows. The app itself supports Python `3.10` through `3.14`, and local development is pinned to Python `3.12` through `.python-version`.

Install uv if needed:

```powershell
winget install --id=astral-sh.uv -e
```

Then let uv provision Python and sync the project environment:

```powershell
uv python install
uv sync
```

Then run the app:

```powershell
uv run dipsy-dolphin
```

Profile data is stored in `%LOCALAPPDATA%\DipsyDolphin\data\profile.json`.

`uv` manages the local `.venv` for you. The Windows packaging scripts use a separate locked environment under `.artifacts/` and do not replace your local dev environment.

`uv sync` also installs the default dev tools from `pyproject.toml`, so commands like `uv run pytest` and `uv run ruff check .` are available right away.

For dependency management, think of `pyproject.toml` like `package.json` and `uv.lock` like a lockfile:

```powershell
uv add <package>
uv remove <package>
uv lock --upgrade-package <package>
```

If another tool still needs a pip-style export, generate one from the lockfile instead of maintaining `requirements.txt` by hand:

```powershell
uv export --format requirements.txt -o requirements.txt
```

## Build Windows installer

Build the standalone Windows app bundle:

```powershell
uv run python -m scripts.windows_build app --clean
```

Build the Windows installer wizard with Inno Setup:

```powershell
uv run python -m scripts.windows_build installer --clean
```

If you prefer Windows-native wrappers, `packaging/windows/build-app.ps1` and `packaging/windows/build-installer.ps1` still exist as thin shims around the Python tooling.

If Inno Setup is not installed yet, one option is:

```powershell
winget install JRSoftware.InnoSetup
```

The generated outputs stay under `.artifacts/`, so the repo root stays clean.

## GitHub releases

Releases now come directly from the version in `pyproject.toml` when changes land on `main`.

- If a push to `main` does not change `project.version`, no release is created.
- If the version changes to a PEP 440 prerelease like `0.1.0b1` or `0.1.0rc1`, GitHub publishes a prerelease tagged `v0.1.0b1` or `v0.1.0rc1`.
- If the version changes to a stable version like `0.1.0`, GitHub publishes a normal release tagged `v0.1.0`.
- Installer assets are named from that same version, for example `DipsyDolphin-Setup-0.1.0b1.exe` or `DipsyDolphin-Setup-0.1.0.exe`.

Typical flow:

```powershell
uv version 0.1.0b1
git commit -am "Bump version to 0.1.0b1"
git push origin main
```

Or for a stable release:

```powershell
uv version 0.1.0
git commit -am "Release 0.1.0"
git push origin main
```

## Controls

- Drag with left click to move the character.
- Right click to open the action menu.
- Double click to open chat.
- Press `Esc` to quit.

## Suggested next additions

- Separate UI constants into a config module if the app grows.
- Add optional LLM-backed replies behind a clearly defined adapter.
- Add an icon and version metadata to the Windows bundle once behavior stabilizes.
- Add automated tests when conversation and persistence logic become more complex.

## AI-friendly workflow

If you are using AI heavily in this repo, start with these files first:

1. `README.md`
2. `AGENTS.md`
3. `TODO.md`
4. `docs/product-brief.md`
5. `docs/rendering-decision.md`
6. `docs/architecture.md`
7. `src/dipsy_dolphin/core/brain.py`
8. `src/dipsy_dolphin/ui/app.py`

That order gives the project purpose, guardrails, architecture, rules, and implementation details before making changes.
