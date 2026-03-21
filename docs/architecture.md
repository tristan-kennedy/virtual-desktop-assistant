# Architecture

## Overview

Dipsy Dolphin is currently a single-process desktop prototype with a small runtime architecture.
The active desktop shell uses PySide6 and the rendering direction is sprite-based animation as documented in `docs/rendering-decision.md`.

Current runtime pieces:

- `main.py` starts the application.
- `dipsy_dolphin.ui.app.AssistantApp` owns windows, menus, drawing, motion, dialogs, and profile persistence hooks.
- `dipsy_dolphin.core.brain.AssistantBrain` owns chat replies, onboarding prompts, and autonomous character lines.
- `dipsy_dolphin.core.models` defines shared dataclasses for profile and session state.
- `dipsy_dolphin.storage.profile_store.ProfileStore` reads and writes local profile data.
- `scripts.windows_build` owns packaging orchestration, while `packaging/windows/` holds launchers and installer assets.

## Runtime flow

1. The console entrypoint runs `dipsy_dolphin.ui.app.run()`.
2. `AssistantApp` creates the pet window and UI bindings.
3. The app loads a persisted `UserProfile` from `%LOCALAPPDATA%` when available.
4. The app creates a fresh `SessionState` and `AssistantBrain` around that profile.
5. Dipsy asks for the user's name and interests at startup if no profile exists yet.
6. User actions or idle timers trigger chat, jokes, status, and autonomous blurts.
7. `AssistantBrain` updates the session state and the app saves profile changes when needed.

## Runtime packages

- `src/dipsy_dolphin/ui/` contains desktop presentation, movement, menus, bubble UI, and later settings screens, all built around PySide6.
- `src/dipsy_dolphin/core/` contains runtime behavior, session state, scheduling, emotion, and character logic.
- `src/dipsy_dolphin/storage/` contains persistence for profile, memory, logs, and permissions.
- `src/dipsy_dolphin/audio/` is reserved for TTS, STT, and audio playback.
- `src/dipsy_dolphin/llm/` is reserved for model providers, prompt assembly, and response shaping.
- `src/dipsy_dolphin/actions/` is reserved for visible, consent-driven computer interactions.

## Design principles

- Safe by default: visible assistant behavior only.
- Small surface area: minimal files and explicit responsibilities.
- UI and decision logic separated enough for future testing.
- Easy for humans and AI tools to navigate quickly.
- Keep rendering decisions documented and separate from core behavior code.

## Rendering direction

- Active UI stack: `PySide6`
- Visual strategy: 2D sprite sheets or frame sequences, not live 3D rendering
- Core logic should emit named states and intents, while the UI layer chooses animations and playback
- The current PySide6 shell is still a prototype renderer and should evolve toward a more explicit sprite-based presentation layer

## Repository shape

- Keep installable runtime code in `src/dipsy_dolphin/`.
- Keep packaging logic in `packaging/windows/`.
- Keep repo-local packaging and release tooling in `scripts/`.
- Keep generated build output in ignored `.artifacts/` folders.
- Keep process and design notes in `docs/`.
- Keep the root small so entry points are obvious.

## Recommended growth path

If the project expands, keep this direction:

- Add `src/dipsy_dolphin/config.py` for colors, timing, and copy constants.
- Add concrete modules inside `src/dipsy_dolphin/llm/`, `src/dipsy_dolphin/audio/`, and `src/dipsy_dolphin/actions/` instead of crowding the root package.
- Grow `src/dipsy_dolphin/ui/` into a fuller PySide6 renderer once the character presentation layer is ready.
- Add automated coverage for conversation, onboarding, and storage behavior when the project needs it.
- Add `docs/decisions/` for major architectural choices.

## Testing priorities

The first logic worth testing lives in `src/dipsy_dolphin/core/brain.py` and `src/dipsy_dolphin/storage/profile_store.py`:

- onboarding parsing behavior
- session summary generation
- reset behavior
- autonomous chatter selection
- profile load/save behavior
- response handling for common chat inputs

## Safety note

This repository should remain a visible assistant. If future work introduces any real system integration, document it clearly, gate it behind explicit consent, and keep it separate from the character and chat layers.
