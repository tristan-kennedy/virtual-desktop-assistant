# Rendering Decision

## Decision

Dipsy Dolphin uses `PySide6` as the desktop UI and rendering stack.

This is a deliberate move away from treating the earlier Tkinter shell as the permanent presentation layer.
Future character presentation, animation, settings, dialogue UI, and richer desktop behavior should continue building on PySide6.

## Why PySide6

- It is a stronger long-term desktop UI foundation than Tkinter for a polished character app.
- It supports richer windowing, layout, animation, event handling, and custom rendering workflows.
- It is a better fit for a theatrical desktop companion with layered visuals, expressive states, and more advanced UI surfaces.
- It keeps the project in Python while allowing a much more professional desktop presentation.

## What This Does Not Mean

- Dipsy is not planned as a true 3D runtime character right now.
- The rendering plan is 2D presentation using sprite sheets or animation frame sequences.
- The goal is "3D-feeling" character presentation through art direction, staging, and animation, not a live 3D model.

## Presentation Model

The planned visual system is sprite-based.

- Dipsy will be represented by 2D frame sequences or sprite sheets.
- Each animation will be a named state with a fixed or configurable frame sequence.
- The renderer will swap frames over time rather than procedurally drawing the full character.
- Visual effects can later be layered on top of the character, such as speech indicators, reaction marks, glow, shadows, or ambient particles.

## Planned Animation States

The rendering system should support at least these state families:

- `idle`
- `walk`
- `talk`
- `think`
- `laugh`
- `surprised`
- `sad`
- `excited`
- `ask`
- `sing`
- `play_game`

Each state may later have variants based on mood, intensity, or direction.

Examples:

- `idle_calm`
- `idle_bouncy`
- `talk_happy`
- `talk_fast`
- `laugh_big`
- `walk_left`
- `walk_right`

## How Animation Will Work

The high-level runtime model should be:

1. The behavior layer decides what Dipsy is doing.
2. The emotion layer decides how Dipsy is feeling.
3. The UI layer chooses an animation state based on behavior plus emotion.
4. The renderer plays the matching frame sequence.
5. The speech bubble and later TTS stay synchronized with the active animation.

Example mappings:

- telling a joke -> `talk_happy`, then `laugh`
- asking to play tic tac toe -> `ask`
- singing a song after approval -> `sing`
- random movement -> `walk_left` or `walk_right`
- waiting on an LLM response -> `think`
- idle chatter -> `talk`
- no action for a while -> `idle`

## Asset Organization Plan

When real animation assets are added, they should be organized explicitly instead of scattered through UI code.

Suggested structure:

```text
assets/
  character/
    dipsy/
      idle/
      walk/
      talk/
      laugh/
      think/
      sing/
      ask/
      reactions/
```

Each animation directory can contain either:

- numbered frame images, or
- a sprite sheet plus metadata

Suggested metadata fields:

- animation name
- frame count
- frame duration
- loop mode
- default anchor point
- optional directional variant

## UI Architecture Implications

This decision affects the runtime package design.

- `src/dipsy_dolphin/ui/` should remain the home for rendering, windows, bubble UI, menus, and later settings.
- The actual renderer should become a dedicated PySide6-oriented UI component rather than being mixed into behavior logic.
- `src/dipsy_dolphin/core/` should never depend on specific frame files or rendering tricks.
- Behavior, emotion, LLM, and action code should communicate through named states, not direct frame manipulation.

That means the correct dependency direction is:

`core -> state names -> ui renderer`

not:

`core -> direct sprite frame decisions`

## Near-Term PySide6 Growth

The base PySide6 shell now exists. The next rendering steps should be:

### Step 1

Keep the current PySide6 shell as the lightweight runtime host while the character presentation system becomes more explicit.

### Step 2

Expand the PySide6 renderer to cover:

- animation states
- bubble styling
- menus and settings
- synchronized reactions
- richer stage effects

### Step 3

Move the dolphin drawing out of one-off painter code and into a more explicit sprite or frame-sequence renderer.

### Step 4

Add data-driven animation playback so behavior and emotion can select named animation states rather than direct drawing logic.

## Constraints

- The app should still feel lightweight and responsive.
- Animation playback should be deterministic enough to sync with speech and emotion states.
- The renderer should support always-on-top desktop presentation.
- The visual system should stay data-driven so art can improve without rewriting the behavior engine.

## Resulting Rule For Future Work

All future character presentation work should assume:

- the permanent direction is `PySide6`
- the visual system is 2D sprite-based
- animation should be state-driven
- core logic should remain renderer-agnostic

If a future change makes that harder instead of easier, it is probably the wrong direction.
