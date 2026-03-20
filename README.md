# Dipsy Dolphin

Dipsy Dolphin is a small Windows desktop pet inspired by old-school assistant apps like BonziBuddy.
The goal is a playful AI-powered virtual assistant with chunky retro graphics, a speech bubble, a robotic voice style, and room to grow into richer desktop-helper behaviors over time.

The current build stays local and visible. It does not perform real malicious actions or silently take over system privileges.

## What the app does

- Shows a floating Tkinter desktop character.
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

- `main.py` - app entry point.
- `src/app.py` - Tkinter window, desktop pet UI, and dialogs.
- `src/brain.py` - chat replies, onboarding flow, and autonomous character lines.
- `src/models.py` - dataclasses for profile and session memory.
- `src/storage.py` - local profile persistence under `%LOCALAPPDATA%`.
- `packaging/windows/` - Windows packaging scripts and the Inno Setup installer definition.
- `.github/workflows/` - CI automation for prerelease and tagged installer builds.
- `docs/architecture.md` - system overview and extension guidance.
- `docs/windows-install.md` - Windows build and local install workflow.
- `AGENTS.md` - repository notes for AI coding agents.
- `prompts/README.md` - prompt ideas and AI workflow notes.
- `tests/README.md` - testing plan and suggested coverage.

## Run locally

Requires Python 3.10+ on Windows.

```bash
python main.py
```

Profile data is stored in `%LOCALAPPDATA%\DipsyDolphin\data\profile.json`.

## Install locally on Windows

Build a local Windows app bundle:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\build-app.ps1
```

Build a real Windows installer wizard with Inno Setup:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\build-installer.ps1
```

If Inno Setup is not installed yet, one option is:

```powershell
winget install JRSoftware.InnoSetup
```

For quick local copy-based testing without the installer wizard:

```powershell
powershell -ExecutionPolicy Bypass -File .\packaging\windows\install-local.ps1 -Build -DesktopShortcut
```

## GitHub releases

The repository is set up for two Windows build paths in GitHub Actions:

- Pushes to `main` build a rolling prerelease named `Dipsy Dolphin Main Prerelease` and attach a fresh installer to the `main-latest` release tag.
- Tags like `v0.1.0` build a versioned installer and publish a normal GitHub Release for that tag.

Typical release flow:

```bash
git tag v0.1.0
git push origin v0.1.0
```

That creates a release installer named like `DipsyDolphin-Setup-0.1.0.exe`.

## Controls

- Drag with left click to move the character.
- Right click to open the action menu.
- Double click to open chat.
- Press `Esc` to quit.

## Suggested next additions

- Add automated tests for onboarding, idle chatter selection, profile persistence, and conversation state.
- Separate UI constants into a config module if the app grows.
- Add optional LLM-backed replies behind a clearly defined adapter.
- Add an icon and version metadata to the Windows bundle once behavior stabilizes.

## AI-friendly workflow

If you are using AI heavily in this repo, start with these files first:

1. `README.md`
2. `AGENTS.md`
3. `docs/architecture.md`
4. `src/brain.py`
5. `src/app.py`

That order gives the project purpose, guardrails, architecture, rules, and implementation details before making changes.
