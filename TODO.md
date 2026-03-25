# TODO

Roadmap for Dipsy Dolphin.

Use this file as the default implementation order unless the user gives a different priority. Work from top to bottom, keep changes visible and clear, and preserve the separation between prompting, execution, and presentation as computer actions arrive.

## Current snapshot

- The runtime is now LLM-first.
- The core dialogue path lives in `dipsy_dolphin/core/controller.py` and `dipsy_dolphin/llm/`.
- Structured model output and an initial action registry are in place.
- The PySide6 shell, presentation controller, and animation state machine are in place.
- The next major gaps are emotion, scheduling, richer dialogue presentation, memory growth, and a fuller function execution interface.

## Phase map

- Phase 1: foundations and architecture (`1-5`)
- Phase 2: character behavior and presentation depth (`6-11`)
- Phase 3: LLM/runtime contracts and function interface growth (`12-18`)
- Phase 4: theatrical polish and longer-term expansion (`19-29`)

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

6. Add an emotion model

- Track mood, energy, excitement, confidence, boredom, and familiarity with the user.
- Use emotion state to drive line choice, animation choice, and idle behavior frequency.
- Keep the model simple and inspectable.
- Done when: identical input can produce different visible behavior based on Dipsy's current emotional state.

7. Link animation to emotion and intent [done]

- Map joke delivery to laugh animation, waiting to think animation, surprise to reaction animation, and so on.
- Tie dialogue categories to both animation cues and bubble styling.
- Done when: a user can infer Dipsy's mood from visuals even with the text hidden.
- Status: completed through `dipsy_dolphin/core/dialogue.py`, `dipsy_dolphin/ui/presentation_policy.py`, `dipsy_dolphin/ui/presentation_controller.py`, and the updated `dipsy_dolphin/ui/app.py` flow.

8. Replace simple idle timing with a behavior scheduler [done]

- Introduce a scheduler that considers time since last interaction, emotion, cooldowns, and user preferences.
- Separate ambient chatter, questions, jokes, reactions, and movement into distinct behavior types.
- Done when: autonomous behavior is state-driven instead of mostly timer-driven.
- Status: completed through `dipsy_dolphin/core/autonomy.py`, `dipsy_dolphin/core/models.py`, `dipsy_dolphin/storage/profile_store.py`, and the scheduler-driven timer flow in `dipsy_dolphin/ui/app.py`.

9. Upgrade the speech bubble and dialogue presentation [done]

- Add clearer line categories, staged reveal, queueing rules, and interruption handling.
- Support different bubble styles for jokes, warnings, thoughts, and normal speech.
- Keep the bubble synchronized with animation and future voice playback.
- Done when: dialogue presentation has enough structure to support richer emotional delivery and voice.
- Status: completed through `dipsy_dolphin/ui/dialogue_presenter.py`, `dipsy_dolphin/ui/presentation_policy.py`, and the queued staged-reveal bubble flow in `dipsy_dolphin/ui/app.py`.

10. Expand memory beyond name and interests [done]

- Split memory into profile, session, long-term facts, preferences, execution history, and tool context.
- Make memory inspectable and deletable by the user.
- Done when: Dipsy can remember multiple categories of user information across sessions.
- Status: completed through `dipsy_dolphin/core/memory.py`, `dipsy_dolphin/storage/memory_store.py`, the `memory_updates` turn contract, prompt wiring, and the new memory menu actions in `dipsy_dolphin/ui/app.py`.

11. Add TTS voice output

- Add a robotic voice pipeline with mute, volume, rate, and interruption controls.
- Sync spoken output with the speech bubble and animation state.
- Keep voice optional so the app still works without audio.
- Done when: Dipsy can speak lines aloud with stable playback controls.

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

14. Build an action and tool registry [done]

- Define a registry of runtime actions or callable tools with id, description, and parameter shape.
- Keep the registry human-readable for review and AI-readable for planning.
- Done when: Dipsy has a single source of truth for what it can currently invoke.
- Status: completed as an initial bootstrap registry in `dipsy_dolphin/actions/registry.py`.

15. Add a fuller function execution layer

- Define attached function interfaces, argument validation, execution results, and error surfaces.
- Keep function execution separate from UI rendering and prompt assembly.
- Support both simple one-shot calls and richer future controller loops.
- Done when: the controller can invoke explicit functions without leaking execution details into the UI host.

16. Add a richer controller execution loop

- Let the model plan, call a function, observe the result, and continue when needed.
- Keep the loop deterministic enough to debug and inspect.
- Make intermediate execution state visible to the runtime.
- Done when: Dipsy can handle multi-step tool-backed interactions without collapsing everything into one prompt.

17. Add user-facing approval, interruption, and review UX

- Show what Dipsy is about to do when the execution path needs user review.
- Support interrupting, retrying, or declining a proposed tool call.
- Keep the UI understandable even when the controller loop gets more capable.
- Done when: the user can follow and steer function-backed execution from the UI.

18. Add execution logs and tool history

- Record proposed tool calls, executed calls, results, failures, and follow-up turns.
- Make the history inspectable from the UI and useful in future prompts.
- Done when: tool-backed behavior can be reviewed and debugged without guesswork.

19. Add app-specific integrations before generic automation

- Build targeted adapters for things like Spotify, browser search, reminders, notes, and other explicit app surfaces.
- Prefer explicit APIs or predictable command paths over fragile UI automation where practical.
- Done when: Dipsy can control a few apps in a robust, reviewable way.

20. Add theatrical scene behaviors

- Create entrance bits, celebration bits, fake panic, joke routines, and idea moments.
- Tie them to animation, bubble styles, and future voice effects.
- Done when: Dipsy has recognizable performative routines beyond basic responses.

21. Improve visuals in passes

- Pass 1: stronger silhouette, color, facial readability, and bubble polish.
- Pass 2: layered effects, better motion, better staging, and more expressive reactions.
- Pass 3: richer sprite structure and stronger pseudo-3D feel if desired.
- Done when: the character looks intentional and memorable instead of prototype-grade.

22. Plan and execute the 3D milestone

- If true 3D remains the goal, define the renderer, asset format, rigging path, and animation import workflow.
- Build a minimum 3D slice before any full migration.
- Done when: a small but real 3D Dipsy path exists and is technically proven.

23. Add a settings and control center

- Add settings for voice, autonomy frequency, model provider, execution behavior, and memory controls.
- Add pause and snooze controls so the user can quiet Dipsy without closing it.
- Done when: the user can manage Dipsy's behavior without editing files manually.

24. Add STT or push-to-talk voice input

- Add push-to-talk first instead of always-listening input.
- Show clear listening and transcript states before any action is taken.
- Done when: the user can talk to Dipsy naturally without losing control over what gets executed.

25. Harden persistence and migrations

- Version storage formats for profiles, memory, settings, execution state, and tool history.
- Add migration logic for future schema changes.
- Protect against partial writes and corrupted state where practical.
- Done when: updates can add features without breaking existing user data.

26. Add observability and debug tooling

- Add logs for behavior selection, emotion changes, model usage, tool calls, failures, and recoveries.
- Add a lightweight debug view or developer mode.
- Done when: odd behavior can be traced without guesswork.

27. Keep expanding automated tests with the runtime

- Add coverage for emotion transitions, scheduling, storage, tool execution, controller loops, and structured LLM output.
- Focus first on non-UI logic.
- Done when: the important assistant logic can change safely without regressions.

28. Polish packaging and releases

- Add app icon, installer branding, version metadata, and better release notes.
- Add smoke checks before automated releases.
- Prepare for code signing once public distribution matters.
- Done when: the release experience feels like a normal Windows desktop product.

29. Roll out richer computer actions in stages

- Stage 1: chatty desktop companion.
- Stage 2: memory, voice, emotion, and richer behavior.
- Stage 3: attached single-step functions.
- Stage 4: app integrations and result-aware controller loops.
- Stage 5: richer multi-step execution.
- Done when: Dipsy's capabilities expand without blurring the boundaries between prompt, execution, and presentation.

## Immediate next sequence

If work resumes soon, the recommended next build order is:

1. `6` emotion model
2. `7` animation-to-emotion and intent mapping
3. `8` behavior scheduler
4. `9` richer speech bubble and dialogue presentation
5. `10` memory expansion
6. `11` TTS voice output
7. `15-18` function execution layer, controller loop, and review surfaces
8. `19` first explicit integrations
