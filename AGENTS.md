# AGENTS.md

## Project intent

Dipsy Dolphin is a playful desktop assistant project inspired by retro companions like BonziBuddy. The current app should stay visibly theatrical, character-driven, and safe.

Agents working in this repo should preserve that framing.

## Hard rules

- Do not add real malicious behavior.
- Do not add code that touches real OS permissions, persistence, registry, credentials, files, processes, or network state unless the user explicitly reframes the project and the change is clearly safe.
- Keep Dipsy's visible behaviors playful and transparent.
- Prefer visible UX over hidden behavior.
- Treat `YOU LOSE` as a theatrical assistant overload state, not a real compromise.

## Code map

- `main.py`: launches the app.
- `src/app.py`: all Tkinter UI behavior.
- `src/brain.py`: conversation logic, onboarding flow, autonomous chatter, and session state.
- `src/models.py`: shared dataclasses for profile and runtime state.
- `src/storage.py`: local profile persistence.
- `packaging/windows/`: Windows packaging scripts and Inno Setup assets.
- `docs/architecture.md`: architectural intent and extension notes.

## Working style

- Keep modules small and explicit.
- Favor simple Python and standard library usage.
- When adding features, separate UI code from assistant logic.
- Prefer deterministic logic for risk and state transitions.
- Add tests for new non-trivial logic when practical.

## Safe extension ideas

- More scripted autonomous behaviors.
- Better status screens or history views.
- Different scripted assistant personalities.
- Session replay or scoring summaries.
- Better chat orchestration and LLM provider adapters.

## Changes to avoid by default

- Real telemetry.
- Background services.
- Autorun behavior.
- Real file inspection.
- Real process control.
- Real network monitoring.

## Good first reads for an AI agent

1. `README.md`
2. `docs/architecture.md`
3. `src/models.py`
4. `src/brain.py`
5. `src/app.py`
