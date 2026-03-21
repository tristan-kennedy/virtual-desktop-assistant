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

- `main.py`: compatibility entry point that still launches the app.
- `TODO.md`: temporary prioritized roadmap for future implementation work.
- `docs/product-brief.md`: product intent, guardrails, and version scope.
- `docs/rendering-decision.md`: long-term rendering stack and animation direction.
- `src/dipsy_dolphin/ui/app.py`: all PySide6 UI behavior.
- `src/dipsy_dolphin/core/brain.py`: conversation logic, onboarding flow, autonomous chatter, and session state.
- `src/dipsy_dolphin/core/models.py`: shared dataclasses for profile and runtime state.
- `src/dipsy_dolphin/storage/profile_store.py`: local profile persistence.
- `scripts/windows_build.py`: Windows packaging orchestration.
- `packaging/windows/`: Windows packaging shims and Inno Setup assets.
- `docs/architecture.md`: architectural intent and extension notes.

## Working style

- Keep modules small and explicit.
- Favor simple Python and standard library usage.
- When adding features, separate UI code from assistant logic.
- Keep packaging and CI files out of `src/`.
- Use `TODO.md` as the default roadmap unless the user asks for a different priority.
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
2. `TODO.md`
3. `docs/product-brief.md`
4. `docs/rendering-decision.md`
5. `docs/architecture.md`
6. `src/dipsy_dolphin/core/models.py`
7. `src/dipsy_dolphin/core/brain.py`
8. `src/dipsy_dolphin/ui/app.py`
