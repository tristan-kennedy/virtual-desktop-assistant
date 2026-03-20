# Architecture

## Overview

ByteBuddy is a single-process Tkinter desktop app with a deliberately small architecture:

- `main.py` starts the application.
- `vda.app.AssistantApp` owns windows, menus, drawing, motion, and dialogs.
- `vda.brain.AssistantBrain` owns chat replies, permission prompts, risk scoring, and failure-state decisions.
- `vda.models` defines shared dataclasses for permission specs and session state.

## Runtime flow

1. `main.py` calls `vda.app.run()`.
2. `AssistantApp` creates the pet window and UI bindings.
3. The app creates a fresh `SessionState` and `AssistantBrain`.
4. User actions trigger chat, jokes, status, or a simulated permission prompt.
5. `AssistantBrain` updates the session state and decides whether the `YOU LOSE` condition should fire.

## Design principles

- Safe by default: simulation only.
- Small surface area: minimal files and explicit responsibilities.
- UI and decision logic separated enough for future testing.
- Easy for humans and AI tools to navigate quickly.

## Recommended growth path

If the project expands, keep this direction:

- Add `vda/config.py` for colors, timing, and copy constants.
- Add `vda/scenarios.py` for reusable scripted permission sequences.
- Add `tests/test_brain.py` for permission and failure-state coverage.
- Add `docs/decisions/` for major architectural choices.

## Testing priorities

The first logic worth testing lives in `vda/brain.py`:

- permission selection behavior
- risk score calculation
- reset behavior
- lose-condition triggering rules
- response handling for common chat inputs

## Safety note

This repository should remain a visible simulator. If future work introduces any real system integration, document it clearly, gate it behind explicit consent, and keep it separate from the current simulation path.
