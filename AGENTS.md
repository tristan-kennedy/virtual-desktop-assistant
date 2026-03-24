# AGENTS.md

## Project intent

Dipsy Dolphin is a playful desktop companion inspired by retro assistants like BonziBuddy. The app should stay visibly theatrical, character-driven, and architecturally clear.

The runtime is now LLM-first: the UI prompts a bundled local model, parses the result into structured assistant turns, and only then applies presentation or execution through explicit runtime interfaces.

## Hard rules

- Keep Dipsy's visible behaviors playful and transparent.
- Prefer visible UX over hidden behavior.
- Keep model-facing intent, execution logic, and UI presentation separate.
- Route computer actions through explicit tool or function interfaces rather than ad-hoc string handling.

## Code map

- `README.md`: current setup, local run flow, packaging, and AI-first reading order.
- `TODO.md`: prioritized roadmap from the current runtime state.
- `docs/product-brief.md`: product intent, guardrails, and version scope.
- `docs/rendering-decision.md`: rendering stack and animation direction.
- `docs/architecture.md`: runtime flow and separation of concerns.
- `dipsy_dolphin/__main__.py`: console entrypoint.
- `dipsy_dolphin/ui/app.py`: PySide6 shell, timers, dialogs, movement, and controller task lifecycle.
- `dipsy_dolphin/core/controller.py`: main dialogue and autonomy coordinator.
- `dipsy_dolphin/core/controller_models.py`: structured turn data contracts.
- `dipsy_dolphin/core/brain.py`: profile parsing and reset helpers, not the main conversation engine.
- `dipsy_dolphin/core/models.py`: shared user/session state.
- `dipsy_dolphin/llm/`: prompt assembly, response parsing, local provider, and model/runtime discovery.
- `dipsy_dolphin/actions/registry.py`: initial action/tool registry.
- `dipsy_dolphin/storage/profile_store.py`: local profile persistence.
- `scripts/windows_build.py`: Windows packaging and model-bundle orchestration.
- `packaging/windows/`: packaging shims and Inno Setup assets.

## Working style

- Keep modules small and explicit.
- Preserve the separation between UI host, controller logic, LLM contract, and action or function interfaces.
- Favor simple Python and standard library usage where practical.
- Keep packaging and CI files out of `dipsy_dolphin/`.
- Use `TODO.md` as the default roadmap unless the user asks for a different priority.
- Prefer deterministic validation around model output and action routing.
- Do not reintroduce large scripted fallback conversation paths unless the user explicitly asks for them.
- Add tests for new non-trivial logic when practical.

## Safe extension ideas

- Better idle behavior scheduling.
- Emotion and mood state that drives presentation.
- Better dialogue presentation or optional voice playback.
- Richer function and tool execution surfaces behind clear controller contracts.
- Better settings and debug views.

## Changes to avoid by default

- Hidden background services.
- Opaque side effects mixed directly into UI code.
- Large unstructured prompt or controller logic blobs.
- Tight coupling between model output and execution behavior.

## Good first reads for an AI agent

1. `README.md`
2. `TODO.md`
3. `docs/architecture.md`
4. `docs/product-brief.md`
5. `docs/rendering-decision.md`
6. `dipsy_dolphin/core/controller.py`
7. `dipsy_dolphin/llm/prompt_builder.py`
8. `dipsy_dolphin/llm/response_parser.py`
9. `dipsy_dolphin/llm/local_provider.py`
10. `dipsy_dolphin/ui/app.py`
11. `dipsy_dolphin/core/models.py`
12. `dipsy_dolphin/core/brain.py`
