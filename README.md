# ByteBuddy

ByteBuddy is a small Windows desktop pet inspired by old-school assistant apps.
This repository is a safe simulation project: the app chats, asks for fake permissions, and can trigger a `YOU LOSE` failure dialog when the user grants a risky combination inside the simulation.

It does not perform real malicious actions or request real system privileges.

## What the app does

- Shows a floating Tkinter desktop character.
- Supports drag-to-move, right-click actions, and quick chat.
- Presents simulated permission prompts with humorous social-engineering language.
- Tracks granted and denied simulated permissions.
- Triggers a visible failure state when a risky simulated combination is granted.

## Safety boundaries

- No privilege escalation.
- No registry edits.
- No startup persistence changes.
- No process, file, or network manipulation.
- No hidden execution or destructive behavior.

## Why this project exists

The goal is to explore how playful UX, trust, and repeated permission prompts can push users toward unsafe decisions.
It is best understood as a security-awareness simulator or failure-state demo, not an offensive tool.

## Current structure

- `main.py` - app entry point.
- `vda/app.py` - Tkinter window, desktop pet UI, and dialogs.
- `vda/brain.py` - chat replies, simulated permission requests, and loss-condition logic.
- `vda/models.py` - dataclasses for session state and permission definitions.
- `docs/architecture.md` - system overview and extension guidance.
- `AGENTS.md` - repository notes for AI coding agents.
- `prompts/README.md` - prompt ideas and AI workflow notes.
- `tests/README.md` - testing plan and suggested coverage.

## Run locally

Requires Python 3.10+ on Windows.

```bash
python main.py
```

## Controls

- Drag with left click to move the character.
- Right click to open the action menu.
- Double click to open chat.
- Press `Esc` to quit.

## Suggested next additions

- Add automated tests for permission scoring and loss conditions.
- Separate UI constants into a config module if the app grows.
- Add scripted demo scenarios for repeatable security-awareness sessions.
- Package the app for Windows once behavior stabilizes.

## AI-friendly workflow

If you are using AI heavily in this repo, start with these files first:

1. `README.md`
2. `AGENTS.md`
3. `docs/architecture.md`
4. `vda/brain.py`
5. `vda/app.py`

That order gives the project purpose, guardrails, architecture, rules, and implementation details before making changes.
