# Product Brief

## Purpose

Dipsy Dolphin is a theatrical desktop companion inspired by retro assistants like BonziBuddy.

The product goal is a visible character that lives on the desktop, talks with personality, reacts to the user, and grows into a capable AI-powered assistant.

The current app already uses a bundled local LLM as Dipsy's core brain.

## Character

- Dipsy is whimsical, playful, mischievous, and warm.
- Dipsy should feel like a tiny performer living on the desktop, not a silent utility.
- Humor matters: jokes, overreactions, theatrical timing, and visible personality are core to the identity.
- Dipsy should be friendly without pretending to be human.
- The voice and visuals should feel stylized, robotic, and retro rather than naturalistic.
- The long-term presentation target is a PySide6 desktop shell with expressive sprite-based animation.

## What "Alive On The Desktop" Means

Dipsy should feel present even when the user is not actively chatting.

- Dipsy idles, wanders, emotes, and occasionally says something in character.
- Dipsy can perform small ambient behaviors like moving to a new spot, reacting visibly, or playing an idle animation.
- Dipsy can spontaneously tell a joke, ask a short question, or make a brief comment.
- Dipsy should not constantly interrupt. Presence should feel charming, not exhausting.
- When the user engages directly, Dipsy should prioritize that interaction over autonomous antics.

## Core loop

The default runtime loop is:

1. Idle visibly on the desktop.
2. Wait for user input or an autonomy timer.
3. Prompt the local LLM with current session state and event context.
4. Parse the result into structured `say`, `animation`, and optional execution intent data.
5. Apply the presentation or route a tool or function request through the runtime interface.
6. Return to idle.

## Behavior categories

- Ambient: idle animation, movement, visual reactions, and presence-only behaviors.
- Spontaneous speech: jokes, short observations, and companion chatter.
- Prompted offers: playful invitations to do something visible.
- Direct conversation: user chats at any time and Dipsy responds through the local LLM path.

Direct user chat should suppress autonomous chatter for a cooldown window so Dipsy does not talk over active interaction.

## Action direction

Dipsy should grow from presentation-only behavior into real computer actions through attached functions and explicit runtime interfaces.

Near-term action goals:

- keep movement and on-screen behavior integrated with the main assistant loop
- add attached functions for concrete computer capabilities
- support richer controller loops where the model can plan, call functions, observe results, and continue

Rules for actions:

- computer actions should be represented as explicit structured intents or tool calls
- execution should remain inspectable in the runtime, not buried in freeform text
- presentation, planning, and execution should stay separable as the interface gets more capable

## Visual direction

- Dipsy should present as a 2D animated character using sprite sheets or frame sequences.
- The goal is expressive animation, not real-time 3D rendering.
- Visual state should be driven by behavior and emotion, so jokes can trigger laugh animation, questions can trigger ask-like reactions, and waiting can trigger thinking.
- The long-term rendering stack is PySide6.

## Guardrails

These rules define the product, not just the implementation.

- Visible UX: Dipsy should remain legible and interruptible as a desktop presence.
- Clear execution surface: computer capabilities should come through explicit functions or tools.
- Structured output: model responses should be parsed and validated before the app uses them.
- Clear logs: when richer execution arrives, the user should be able to inspect what Dipsy proposed and what actually ran.
- Separation of concerns: keep model prompting, execution logic, and UI presentation distinct.

## Interruption policy

Interruptions are welcome when they are short, theatrical, and low-stakes.

Good interruptions:

- a joke
- a random fact or thought
- a small visual reaction
- moving somewhere else on the screen
- a short playful offer

Bad interruptions:

- repeated chatter during active conversation
- long unsolicited routines
- any system action that feels confusing, opaque, or out of sync with the visible character
- anything that feels spammy or detached from the desktop persona

## Version scope

### V1

Goal: a polished local-LLM desktop companion.

- bundled local LLM-backed chat and autonomy
- structured model output with a clean controller boundary
- stronger visual identity and animation states
- local profile and memory basics
- stable Windows installer and release pipeline

V1 is done when Dipsy feels lively, readable, and consistent as a local AI desktop companion.

### V2

Goal: richer behavior orchestration and presentation.

- emotion and mood state
- better autonomous scheduling
- stronger memory model and user-facing controls
- better dialogue presentation and optional TTS
- settings and debug surfaces

V2 is done when Dipsy feels consistently alive, expressive, and inspectable over longer sessions.

### V3

Goal: a desktop assistant with attached computer functions and richer execution loops.

- broader function and tool interface
- execution loop that can incorporate function results back into the conversation
- audit log
- first real integrations such as Spotify, reminders, browser actions, or app control

V3 is done when Dipsy can perform useful desktop tasks through explicit runtime interfaces without collapsing the separation between character, controller, and execution.

## Non-goals for now

- vague capability claims that are not backed by real runtime interfaces
- opaque controller logic that mixes prompting, planning, and execution together
- desktop actions that bypass the structured runtime path
- UI code that directly owns tool execution details

## Product test

If a future feature is proposed, it should pass this check:

"Does this make Dipsy feel more alive, more theatrical, more helpful, and still clearly under the user's control?"

If not, it is off-track.
