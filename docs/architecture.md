# Architecture

## Overview

Dipsy Dolphin is a single-process desktop app with an LLM-first runtime.

The active desktop shell uses PySide6 and the rendering direction is sprite-style presentation as documented in `docs/rendering-decision.md`. The UI asks a bundled local LLM what Dipsy should do, validates the model response, and then applies either presentation changes or execution through explicit runtime interfaces.

## Runtime flow

1. `dipsy_dolphin.__main__` runs `dipsy_dolphin.ui.app.run()`.
2. `dipsy_dolphin.ui.app.AssistantApp` creates the pet window, bubble UI, timers, and menus.
3. The app loads a `UserProfile` from `%LOCALAPPDATA%` through `dipsy_dolphin.storage.profile_store.ProfileStore`.
4. The app creates a fresh `SessionState` and an `AssistantController`.
5. `AssistantController` builds a system prompt and event payload through `dipsy_dolphin.llm.prompt_builder`.
6. `dipsy_dolphin.llm.local_provider.LocalLlamaProvider` locates the bundled model and llama.cpp runtime, starts the local server if needed, and requests a response.
7. `dipsy_dolphin.llm.response_parser` extracts and sanitizes the JSON into an `AssistantTurn` with dialogue category, animation hint, emotion, and action data.
8. `dipsy_dolphin.actions.registry` validates any requested action id against the current tool registry.
9. `AssistantApp` applies the returned speech, animation, and any execution result to the UI and persists profile updates when needed.

## Runtime modules

### UI host

- `dipsy_dolphin/ui/app.py` owns the PySide6 shell, request lifecycle, onboarding dialogs, movement, bubble timing, dialogue queue timers, and the single Qt timer that drives autonomy checks.
- `dipsy_dolphin/ui/animation_state_machine.py` tracks active animation state, priorities, and cooldowns.
- `dipsy_dolphin/ui/dialogue_presenter.py` owns staged reveal, queueing, and interruption rules for visible dialogue.
- `dipsy_dolphin/ui/presentation_policy.py` maps semantic turn cues into animation and bubble-style decisions.
- `dipsy_dolphin/ui/presentation_controller.py` maps those cues plus emotion into render-friendly presentation values.
- `dipsy_dolphin/ui/character_widget.py`, `dipsy_dolphin/ui/character_renderer.py`, and `dipsy_dolphin/ui/asset_manifest.py` render the character and expose layout anchors.

### Decision layer

- `dipsy_dolphin/core/controller.py` is the main runtime coordinator.
- `dipsy_dolphin/core/controller_models.py` defines the structured turn contract used between the controller and UI.
- `dipsy_dolphin/core/brain.py` is now intentionally small: it parses profile facts from user text and resets state. It is not the main conversation engine.
- `dipsy_dolphin/core/models.py` defines shared user/session dataclasses.
- `dipsy_dolphin/core/memory.py` defines structured memory sections and validated LLM-authored memory updates.

### LLM contract

- `dipsy_dolphin/llm/prompt_builder.py` defines the prompt contract and event-specific instructions.
- `dipsy_dolphin/llm/response_parser.py` turns raw model output into validated structured data.
- `dipsy_dolphin/llm/provider.py` defines the provider protocol.
- `dipsy_dolphin/llm/local_provider.py` implements the bundled local provider.
- `dipsy_dolphin/llm/config.py`, `dipsy_dolphin/llm/model_catalog.py`, and `dipsy_dolphin/llm/runtime_catalog.py` define discovery and bundle metadata.

### Function and action interface

- `dipsy_dolphin/actions/registry.py` is the current source of truth for action ids and sanitization.
- This registry is the bootstrap version of a broader function and tool execution surface.
- Model output should continue flowing through structured runtime contracts rather than ad-hoc string execution.

### Persistence and packaging

- `dipsy_dolphin/storage/profile_store.py` currently handles local profile persistence.
- `dipsy_dolphin/storage/memory_store.py` persists long-term memory separately from the profile.
- `scripts/windows_build.py` owns packaging, model download, runtime download, and installer orchestration.
- `packaging/windows/` contains launchers and Inno Setup assets.

## Design principles

- LLM-first: use a local model for the core brain and keep the hot path explicit.
- Visible behavior: Dipsy should remain theatrical on screen even as execution grows.
- Small explicit modules: keep the hot path readable for both humans and AI tools.
- Clear dependency direction: controller decides intent, UI decides presentation, renderer decides pixels.
- Explicit interfaces: computer capability should flow through well-defined action or function contracts.

## Repository shape

- Keep installable runtime code in `dipsy_dolphin/`.
- Keep packaging logic in `packaging/windows/`.
- Keep repo-local tooling in `scripts/`.
- Keep generated build output in ignored `.artifacts/` folders.
- Keep design notes in `docs/`.

## Recommended growth path

- Add an emotion or mood layer inside `dipsy_dolphin/core/` that feeds animation and dialogue style.
- Grow the existing autonomous behavior scheduler with richer preferences and memory as needed.
- Expand storage carefully for memory, settings, tool history, and execution state when those systems land.
- Grow `dipsy_dolphin/actions/` from the current registry into a fuller function and tool execution layer.
- Add `docs/decisions/` if the architecture starts gaining more major irreversible choices.

## Testing priorities

The most valuable non-UI contracts right now are:

- controller behavior and required-turn guardrails in `tests/test_controller.py`
- prompt and parsing contract behavior in `tests/test_response_parser.py`
- model discovery rules in `tests/test_llm_config.py`
- presentation state rules in `tests/test_animation_state_machine.py` and `tests/test_presentation_controller.py`
- profile persistence and profile parsing helpers in `tests/test_profile_store.py` and `tests/test_brain.py`

## Safety note

This repository should remain a visible assistant. As computer actions arrive, keep them routed through explicit interfaces and keep the action layer separate from the character and chat layers.
