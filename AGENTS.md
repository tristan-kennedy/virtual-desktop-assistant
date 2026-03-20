# AGENTS.md

## Project intent

ByteBuddy is a safe desktop simulation project. It presents fake permission prompts and a visible failure state to demonstrate risky user decisions in a playful way.

Agents working in this repo should preserve that framing.

## Hard rules

- Do not add real malicious behavior.
- Do not add code that touches real OS permissions, persistence, registry, credentials, files, processes, or network state unless the user explicitly reframes the project and the change is clearly safe.
- Keep permission prompts simulated and transparent.
- Prefer visible UX over hidden behavior.
- Treat `YOU LOSE` as an educational failure state, not a real compromise.

## Code map

- `main.py`: launches the app.
- `vda/app.py`: all Tkinter UI behavior.
- `vda/brain.py`: conversation logic, permission sequencing, risk state, and lose-condition checks.
- `vda/models.py`: small shared dataclasses.
- `docs/architecture.md`: architectural intent and extension notes.

## Working style

- Keep modules small and explicit.
- Favor simple Python and standard library usage.
- When adding features, separate UI code from simulation logic.
- Prefer deterministic logic for risk and state transitions.
- Add tests for new non-trivial logic when practical.

## Safe extension ideas

- More simulated permission types.
- Better status screens or history views.
- Different scripted demo personalities.
- Session replay or scoring summaries.
- Tutorial mode explaining why each prompt is risky.

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
3. `vda/models.py`
4. `vda/brain.py`
5. `vda/app.py`
