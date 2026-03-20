# Architecture

## Overview

Dipsy Dolphin is a single-process Tkinter desktop app with a deliberately small architecture:

- `main.py` starts the application.
- `src.app.AssistantApp` owns windows, menus, drawing, motion, dialogs, and profile persistence hooks.
- `src.brain.AssistantBrain` owns chat replies, onboarding prompts, and autonomous character lines.
- `src.models` defines shared dataclasses for profile and session state.
- `src.storage.ProfileStore` reads and writes local profile data.
- `packaging/windows` contains build scripts and the Inno Setup installer definition.

## Runtime flow

1. `main.py` calls `src.app.run()`.
2. `AssistantApp` creates the pet window and UI bindings.
3. The app loads a persisted `UserProfile` from `%LOCALAPPDATA%` when available.
4. The app creates a fresh `SessionState` and `AssistantBrain` around that profile.
5. Dipsy asks for the user's name and interests at startup if no profile exists yet.
6. User actions or idle timers trigger chat, jokes, status, and autonomous blurts.
7. `AssistantBrain` updates the session state and the app saves profile changes when needed.

## Design principles

- Safe by default: visible assistant behavior only.
- Small surface area: minimal files and explicit responsibilities.
- UI and decision logic separated enough for future testing.
- Easy for humans and AI tools to navigate quickly.

## Recommended growth path

If the project expands, keep this direction:

- Add `src/config.py` for colors, timing, and copy constants.
- Add `src/llm.py` or `src/providers.py` for model integration behind a narrow interface.
- Add `tests/test_brain.py` for conversation and onboarding coverage.
- Add `tests/test_storage.py` for persisted profile coverage.
- Add `docs/decisions/` for major architectural choices.

## Testing priorities

The first logic worth testing lives in `src/brain.py` and `src/storage.py`:

- onboarding parsing behavior
- session summary generation
- reset behavior
- autonomous chatter selection
- profile load/save behavior
- response handling for common chat inputs

## Safety note

This repository should remain a visible assistant. If future work introduces any real system integration, document it clearly, gate it behind explicit consent, and keep it separate from the character and chat layers.
