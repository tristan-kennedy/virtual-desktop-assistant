# Product Brief

## Purpose

Dipsy Dolphin is a theatrical desktop companion inspired by retro assistants like BonziBuddy.
The product goal is not a hidden agent or background controller. It is a visible character that lives on the desktop, talks with personality, reacts to the user, and gradually grows into a capable AI-powered assistant.

## Character

- Dipsy is whimsical, playful, mischievous, and warm.
- Dipsy should feel like a tiny performer living on the desktop, not a silent utility.
- Humor matters: jokes, laughing, overreactions, and theatrical timing are core to the identity.
- Dipsy should be friendly without pretending to be human.
- The voice and visuals should feel stylized, robotic, and retro rather than naturalistic.
- The long-term presentation target is a PySide6 desktop shell with sprite-based animation.

## What "Alive On The Desktop" Means

Dipsy should feel present even when the user is not actively chatting.

- Dipsy idles, wanders, emotes, and occasionally blurts out something in character.
- Dipsy can perform small ambient behaviors like moving to a new spot, reacting visibly, or playing an idle animation.
- Dipsy can spontaneously tell a joke, say a fact, or make a short comment.
- Dipsy should not constantly interrupt. Presence should feel charming, not exhausting.
- When the user engages directly, Dipsy should prioritize that conversation over autonomous antics.

## Core Loop

The default runtime loop is:

1. Idle
2. Wait a random amount of time
3. Choose a behavior
4. Either say something, ask to do something, move, animate, or remain quiet
5. Return to idle

Behavior categories:

- Ambient: idle animation, movement, visual reaction, presence-only behaviors
- Spontaneous speech: random joke, random fact, short idle chatter
- Prompted offers: asking whether the user wants a song, tic tac toe, or another consensual routine
- Direct conversation: user chats at any time and Dipsy responds through an LLM-backed conversation path

Direct user chat suppresses autonomous random behavior for a cooldown window so Dipsy does not talk over an active interaction.

## Planned Near-Term Actions

The first explicit Dipsy actions should be simple and character-driven.

Random or ambient actions:

- tell a joke
- tell a fact
- idle chatter
- move to another place on the screen
- play an idle animation or visual reaction

Consensual prompted actions:

- play tic tac toe
- sing a song

Rules for these behaviors:

- Jokes, facts, and idle chatter may happen spontaneously.
- Tic tac toe and song must be offered first and only happen after user approval.
- The user can always begin chatting manually, regardless of what Dipsy was about to do.

## Visual Direction

- Dipsy should present as a 2D animated character using sprite sheets or frame sequences.
- The goal is expressive animation, not real-time 3D rendering.
- Visual state should be driven by behavior and emotion, so jokes can trigger laugh animation, questions can trigger ask animation, and idle moments can trigger ambient loops.
- The long-term rendering stack is PySide6.

## Long-Term Action Direction

Later, Dipsy may gain richer computer actions, but they must stay visible, reviewable, and consent-driven.

- Some future actions may happen as spontaneous offers.
- Some future actions may be triggered by direct user chat.
- High-trust actions must never be implied or hidden.
- Every real system action must be explainable in plain language before it runs.

## Guardrails

These rules define the product, not just the implementation.

- Visible actions only: Dipsy should act in ways the user can see, understand, and interrupt.
- Explicit consent: anything beyond harmless chatter or harmless animation should be confirmed when needed.
- Reversible operations: prefer actions that can be undone or safely previewed.
- Clear logs: when real actions are added, the user should be able to inspect what Dipsy proposed and what actually ran.
- Bounded trust: Dipsy should earn more responsibility through clear permissions, not vague implied authority.
- Normal LLM safety: chat can be broad and flexible, but should still rely on the model provider's normal safety boundaries.

## Interruption Policy

Interruptions are welcome when they are short, theatrical, and low-stakes.

Good interruptions:

- a joke
- a random fact
- a small visual reaction
- moving somewhere else on the screen
- asking whether the user wants a playful routine like a song or tic tac toe

Bad interruptions:

- repeated chatter during active conversation
- long unsolicited routines
- any system action without a clear request or explicit consent
- anything that feels hidden, persistent, or spammy

## Version Scope

### V1

Goal: a polished scripted desktop companion.

- stronger visual identity
- better idle behavior
- animation states tied to emotion and line type
- jokes, facts, idle chatter, songs, and tic tac toe offers
- local profile and memory basics
- stable Windows installer and release pipeline

V1 is done when Dipsy feels alive, expressive, and fun even without real AI actions.

### V2

Goal: a real AI conversation layer.

- LLM-backed chat responses
- structured prompt assembly from memory and current context
- cooldown-aware interaction loop
- speech output and better dialogue presentation
- stronger memory model and user-facing controls

V2 is done when chatting with Dipsy feels meaningfully conversational and consistent with the character.

### V3

Goal: a supervised assistant with visible computer actions.

- action registry
- permission and consent system
- action logs
- low-risk app and file interactions
- first real integrations such as Spotify or other explicit adapters

V3 is done when Dipsy can safely perform useful desktop tasks under visible user control.

## Non-Goals For Now

- hidden background automation
- silent system inspection
- broad autonomous control of the computer
- invisible persistence tricks
- deceptive or malicious behavior

## Product Test

If a future feature is proposed, it should pass this check:

"Does this make Dipsy feel more alive, more theatrical, more helpful, and still clearly under the user's control?"

If not, it is off-track.
