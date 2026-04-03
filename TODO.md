# TODO

Roadmap for Dipsy Dolphin.

Use this file as the default implementation order unless the user gives a different priority. Work from top to bottom, keep changes visible and clear, and preserve the separation between chat-first control, internal execution, and presentation.

## Current snapshot

- The runtime is now LLM-first and chat-first.
- Emotion, inactivity scheduling, richer dialogue presentation, structured memory, and TTS are in place.
- Structured action execution and a bounded controller loop are in place.
- The shell is now character plus conversation, without menu-driven controls.
- The next major gaps are stronger visual polish, push-to-talk or STT, persistence hardening, and developer observability.

## Phase map

- Phase 1: foundations and architecture (`1-5`)
- Phase 2: character behavior and presentation depth (`6-11`)
- Phase 3: LLM/runtime contracts and first assistant capabilities (`12-17`)
- Phase 4: theatrical polish and longer-term expansion (`18-26`)

## Roadmap

1. Define the product brief [done]

- Write a short project brief for Dipsy's personality, tone, behavior boundaries, and target experience.
- Done when: there is a committed product brief in `docs/` that future work can reference.
- Status: completed in `docs/product-brief.md`.

2. Lock the long-term architecture [done]

- Define clear boundaries for UI host, controller logic, LLM contract, storage, and execution interfaces.
- Keep runtime logic in `dipsy_dolphin/` and packaging logic outside it.
- Done when: the architecture doc names the main runtime modules and their responsibilities.
- Status: completed in `docs/architecture.md` and the current package layout.

3. Decide the rendering strategy [done]

- Document the rendering direction and keep it separate from core assistant logic.
- Done when: the visual path is clearly state-driven and PySide6-based.
- Status: completed in `docs/rendering-decision.md`.

4. Build a real character presentation layer [done]

- Replace one-off character drawing assumptions with a reusable presentation system.
- Support pose, expression, eye, mouth, and lightweight effect layers.
- Done when: Dipsy can change presentation state without hardcoding every case into one UI branch.
- Status: completed through `dipsy_dolphin/ui/presentation_controller.py`, `dipsy_dolphin/ui/presentation_models.py`, `dipsy_dolphin/ui/character_widget.py`, and `dipsy_dolphin/ui/character_renderer.py`.

5. Add an animation state machine [done]

- Define animation states like `idle`, `walk`, `talk`, `think`, `laugh`, `surprised`, `sad`, and `excited`.
- Add transition rules, priorities, and cooldowns.
- Done when: Dipsy visibly changes animation state based on what it is doing.
- Status: completed in `dipsy_dolphin/ui/animation_state_machine.py`.

6. Add an emotion model [done]

- Track mood, energy, excitement, confidence, boredom, and familiarity with the user.
- Use emotion state to drive line choice, animation choice, and idle behavior frequency.
- Keep the model simple and inspectable.
- Done when: identical input can produce different visible behavior based on Dipsy's current emotional state.
- Status: completed through `dipsy_dolphin/core/emotion.py`, controller state updates, prompt wiring, and emotion-focused tests.

7. Link animation to emotion and intent [done]

- Map joke delivery to laugh animation, waiting to think animation, surprise to reaction animation, and so on.
- Tie dialogue categories to both animation cues and bubble styling.
- Done when: a user can infer Dipsy's mood from visuals even with the text hidden.
- Status: completed through `dipsy_dolphin/core/dialogue.py`, `dipsy_dolphin/ui/presentation_policy.py`, `dipsy_dolphin/ui/presentation_controller.py`, and the updated `dipsy_dolphin/ui/app.py` flow.

8. Replace simple idle timing with neutral inactivity scheduling [done]

- Introduce scheduling that considers time since user interaction, emotion, cooldowns, and current activity.
- Trigger neutral inactivity turns and let the LLM decide whether to stay silent, speak, emote, or act.
- Done when: autonomous behavior is state-driven, pauses during active interaction, and no longer relies on preselected behavior modes.
- Status: completed through `dipsy_dolphin/core/autonomy.py`, `dipsy_dolphin/core/models.py`, `dipsy_dolphin/storage/profile_store.py`, and the inactivity-driven timer flow in `dipsy_dolphin/ui/app.py`.

9. Upgrade the speech bubble and dialogue presentation [done]

- Add clearer line categories, staged reveal, queueing rules, interruption handling, and stronger bubble presentation.
- Support different bubble styles for jokes, warnings, thoughts, and normal speech.
- Keep the bubble synchronized with animation and voice playback.
- Done when: dialogue presentation has enough structure to support richer emotional delivery and voice.
- Status: completed through `dipsy_dolphin/ui/dialogue_presenter.py`, `dipsy_dolphin/ui/presentation_policy.py`, `dipsy_dolphin/ui/bubble_layout.py`, and the staged-reveal bubble flow in `dipsy_dolphin/ui/app.py`.

10. Expand memory beyond name and interests [done]

- Split memory into structured identity, long-term facts, preferences, and runtime context.
- Keep LLM-authored memory updates explicit and controller-applied.
- Done when: Dipsy can remember multiple categories of user information across sessions.
- Status: completed through `dipsy_dolphin/core/memory.py`, `dipsy_dolphin/storage/memory_store.py`, the `memory_updates` turn contract, and prompt/controller wiring.

11. Add TTS voice output [done]

- Add a retro voice pipeline with mute, interruption, and playback timing controls.
- Sync spoken output with the speech bubble and animation state.
- Keep voice optional so the app still works without audio.
- Done when: Dipsy can speak lines aloud with consistent timing and stable interruption behavior.
- Status: completed through `dipsy_dolphin/voice/`, `dipsy_dolphin/ui/dialogue_presenter.py`, and the voice-backed dialogue flow in `dipsy_dolphin/ui/app.py`.

12. Add an LLM provider layer [done]

- Create a provider interface for local and later hosted backends.
- Build prompt assembly from profile, recent chat, and current context.
- Make local-model setup explicit and fail clearly when the bundled brain is unavailable.
- Done when: the app can generate turns through a provider boundary without UI-specific logic in the provider.
- Status: completed through `dipsy_dolphin/llm/provider.py`, `dipsy_dolphin/llm/prompt_builder.py`, `dipsy_dolphin/llm/local_provider.py`, and bundle discovery modules.

13. Separate saying from acting [done]

- Represent assistant turns as structured output with `say`, `animation`, and `action` parts.
- Keep execution requests behind structured controller contracts instead of freeform strings.
- Add parsing and validation before any action can run.
- Done when: every action request passes through a structured internal format first.
- Status: completed through `dipsy_dolphin/core/controller_models.py` and `dipsy_dolphin/llm/response_parser.py`.

14. Build an action registry [done]

- Define a registry of runtime actions or callable capabilities with id, description, and parameter shape.
- Keep the registry human-readable for development and AI-readable for planning.
- Done when: Dipsy has a single source of truth for what it can currently invoke.
- Status: completed as the current bootstrap registry in `dipsy_dolphin/actions/registry.py`.

15. Add a fuller execution layer [done]

- Define explicit execution interfaces, argument validation, execution results, and error surfaces.
- Keep execution separate from UI rendering and prompt assembly.
- Support both simple one-shot calls and richer future controller loops.
- Done when: the controller can invoke explicit actions without leaking execution details into the UI host.
- Status: completed through `dipsy_dolphin/actions/executor.py`, `dipsy_dolphin/actions/models.py`, `dipsy_dolphin/ui/execution.py`, and the controller execution-result flow.

16. Add a richer controller execution loop [done]

- Let the model plan, call an action, observe the result, and continue when needed.
- Keep the loop deterministic enough to debug and inspect.
- Make intermediate execution state visible to the runtime.
- Done when: Dipsy can handle multi-step capability-backed interactions without collapsing everything into one prompt.
- Status: completed through the bounded loop in `dipsy_dolphin/core/controller.py`, `ControllerLoopStep`, and the `action_result` follow-up prompt contract.

17. Add first real assistant capabilities through chat [done]

- Build targeted adapters for things like Spotify, browser search, reminders, notes, and other explicit app surfaces.
- Invoke them through conversation and structured runtime actions rather than separate UI controls.
- Prefer explicit APIs or predictable command paths over fragile UI automation where practical.
- Done when: Dipsy can complete a few useful desktop tasks through chat in a robust, debuggable way.
- Status: completed through the Windows desktop backend in `dipsy_dolphin/desktop/`, typed action validation in `dipsy_dolphin/actions/registry.py`, executor-backed desktop actions in `dipsy_dolphin/actions/executor.py`, and updated prompt/controller wiring for app launch, focus, URL open, path open, and browser search.

18. Add theatrical scene behaviors [done]

- Create entrance bits, celebration bits, fake panic, joke routines, and idea moments.
- Tie them to animation, bubble styles, and future voice effects.
- Done when: Dipsy has recognizable performative routines beyond basic responses.
- Status: completed through `dipsy_dolphin/core/scenes.py`, the `scene_kind` turn contract, scene-aware prompt/controller wiring, presentation overlays, dedicated UI routine events, and the new scene-focused tests.

19. Improve visuals in passes

- Pass 1: stronger silhouette, color, facial readability, and bubble polish.
- Pass 2: layered effects, better motion, better staging, and more expressive reactions.
- Pass 3: richer sprite structure, stronger depth cues, and more convincing 2D stagecraft.
- Done when: the character looks intentional and memorable instead of prototype-grade.

20. Deepen the 2D performance illusion

- Keep the long-term target as 2D art and animation that feels dimensional through staging, motion, layering, and sprite structure.
- Define the asset organization and rendering improvements needed for a BonziBuddy-style 2D character that reads as lively and depthful without becoming a real 3D runtime.
- Build a small proof slice for stronger 2D depth cues before any broader visual overhaul.
- Runtime asset format:
  - use transparent `.png` frame sequences for runtime assets, not GIF, video, or real-time 3D formats
  - keep one `animation.json` beside each animation sequence
  - keep character-level anchors and supported states in `assets/character/dipsy/manifest.json`
- Runtime asset layout:
  - `assets/character/dipsy/manifest.json`
  - `assets/character/dipsy/poses/<pose_id>/animation.json`
  - `assets/character/dipsy/poses/<pose_id>/0001.png`, `0002.png`, and so on
  - `assets/character/dipsy/effects/<effect_id>/0001.png` etc for optional overlay fx loops
  - `assets/character/dipsy/expressions/` only if we later split face layers from the body; do not block the first sprite pass on layered facial assets
- Required first animation families to create:
  - `idle`: subtle bob, blink, tail sway; 6-8 frames loop
  - `walk`: readable side-step cycle; 8 frames loop
  - `talk`: speaking loop for normal dialogue; 4-6 frames loop
  - `think`: small pondering loop; 4-6 frames loop
  - `laugh`: broader mouth and body bounce; 4-6 frames loop
  - `surprised`: quick hit plus settle; 3-4 frames
  - `sad`: lower-energy loop or held settle; 3-4 frames
  - `excited`: bigger bounce and arm/tail lift; 4-6 frames loop
  - `loading`: optional short loop for startup/loading if it stays visually distinct from `think`
- First polish variants after the base set exists:
  - `idle_bouncy`
  - `talk_bright`
  - `laugh_big`
  - `excited_bounce`
  - directional variants only if runtime mirroring looks wrong; otherwise author right-facing sprites first and mirror for left
- File and export rules:
  - every frame in one animation must use the same canvas size and transparent background
  - keep feet planted to a stable baseline so current `feet_anchor` logic still makes sense
  - keep bubble/look anchors consistent with the character root in `manifest.json`
  - prefer lossless RGBA PNG exports
  - keep filenames zero-padded and sequential so playback is trivial to implement
- `animation.json` fields to expect:
  - `pose_id`
  - `frame_count`
  - `fps` or `frame_duration_ms`
  - `loop`
  - `hold_on_last_frame_ms`
  - optional `mirror_safe`
  - optional `notes` for staging or emotion usage
- Proof slice to build before a full asset push:
  - one polished `idle`
  - one polished `talk`
  - one polished `excited`
  - one overlay effect loop like `spark`
  - renderer support that can load those files from `assets/character/dipsy/poses/` instead of procedural drawing for that slice
- Done when: Dipsy feels more dimensional and performative on screen while remaining fully 2D in runtime and asset direction.

25. Polish packaging and releases

- Add app icon, installer branding, version metadata, and better release notes.
- Add smoke checks before automated releases.
- Prepare for code signing once public distribution matters.
- Done when: the release experience feels like a normal Windows desktop product.

26. Roll out richer computer actions in stages

- Stage 1: chatty desktop companion.
- Stage 2: memory, voice, emotion, and richer presence.
- Stage 3: structured single-step capabilities behind chat.
- Stage 4: app integrations and conversation-driven assistant behaviors.
- Stage 5: broader multi-step capabilities if they still improve the assistant feel.
- Done when: Dipsy's capabilities expand without blurring the boundaries between prompt, execution, and presentation.

## Immediate next sequence

If work resumes soon, the recommended next build order is:

1. `19` visual improvement passes
2. `21` push-to-talk or STT
3. `22` persistence hardening
4. `23` developer observability and debug tooling
5. `24` test expansion
6. `25` packaging and release polish
7. `26` broader staged computer-action rollout

## Desktop capability enhancements

These are follow-up improvements to the current desktop-control slice and should stay behind the same chat-first, structured-action runtime path.

- Expand app opening beyond the fixed catalog:
  - add alias maps for common app names like Chrome, Edge, Firefox, VS Code, Obsidian, Discord, and Spotify
  - support direct executable-style names when they can be resolved safely
  - search installed apps or Start Menu shortcuts before giving up
  - allow fuzzy matching against known app aliases and visible window titles, with a clear follow-up when the match is ambiguous

- Expand file and folder opening beyond literal existing paths:
  - resolve relative paths, home-directory shortcuts, and environment-variable paths
  - detect quoted or obvious file paths in chat more reliably
  - search a bounded set of likely folders for direct file-name requests when the user does not provide a full path
  - support fuzzy file-name matching with visible clarification when more than one candidate fits

- Improve “try anyway” behavior while staying transparent:
  - attempt best-effort resolution for direct app and file references instead of hard failing immediately
  - report the resolved target back in the follow-up line so the user can see what Dipsy actually opened
  - require confirmation when fuzzy matching would otherwise open the wrong app, file, or folder

- Broaden the desktop action surface carefully:
  - add explicit actions for open-with-app, reveal-in-Explorer, and focus-existing-window-by-title
  - preserve bounded validation and avoid falling back to raw shell commands

- Keep improving the prompt and controller contract:
  - teach the model when to prefer exact path open, fuzzy target resolution, browser search, or app focus
  - include structured ambiguity and resolution results in action observations so follow-up turns stay grounded
