# TODO

Temporary roadmap for Dipsy Dolphin.

Use this file as the default implementation order unless the user gives a different priority.
Work from top to bottom, keep changes visible and safe, and do not skip consent and audit features before adding real computer actions.

## Phase map

- Phase 1: foundations and architecture (`1-3`)
- Phase 2: character presentation and behavior (`4-9`)
- Phase 3: memory and AI conversation (`10-12`)
- Phase 4: actions, permissions, and integrations (`13-18`)
- Phase 5: theatrical polish and 3D path (`19-21`)
- Phase 6: settings, reliability, and shipping quality (`22-28`)

## Roadmap

1. Define the product brief [done]
- Write a short project brief for Dipsy's personality, tone, behavior boundaries, and target experience.
- Define what Dipsy is allowed to interrupt with and what should always wait for the user.
- Write version goals for `v1`, `v2`, and `v3`.
- Done when: there is a committed project brief in `docs/` that future work can reference.
- Status: completed in `docs/product-brief.md`.

2. Lock the long-term architecture [done]
- Define clear boundaries for UI, behavior, memory, LLM, audio, and actions.
- Keep runtime logic in `src/` and packaging/release logic outside it.
- Add planned interfaces for renderer, emotion engine, scheduler, LLM provider, and action registry.
- Done when: the architecture doc names the main runtime modules and their responsibilities.
- Status: completed through the `src/dipsy_dolphin/ui/`, `src/dipsy_dolphin/core/`, `src/dipsy_dolphin/storage/`, `src/dipsy_dolphin/audio/`, `src/dipsy_dolphin/llm/`, and `src/dipsy_dolphin/actions/` package layout.

3. Decide the rendering strategy [done]
- Choose whether to stay with Tkinter short-term and fake 3D, or plan a renderer migration for real 3D later.
- Document the long-term rendering target if true 3D is still the goal.
- Avoid mixing rendering experiments directly into core assistant logic.
- Done when: there is a written rendering decision and the next visual work has a clear technical path.
- Status: completed in `docs/rendering-decision.md` with PySide6 chosen and now active as the sprite-based rendering stack.

4. Build a real character presentation layer
- Replace one-off character drawing assumptions with a reusable presentation system.
- Support poses, expressions, eye states, mouth states, and effect layers.
- Make the character asset pipeline explicit so visuals can improve without rewriting logic.
- Done when: Dipsy can swap expressions and presentation states without hardcoding every case into the main UI flow.

5. Add an animation state machine
- Define animation states like `idle`, `talk`, `think`, `laugh`, `surprised`, `sad`, and `excited`.
- Add transition rules and cooldowns so state changes feel intentional.
- Connect autonomous behavior and chat responses to animation changes.
- Done when: Dipsy visibly changes animation state based on what it is doing.

6. Add an emotion model
- Track mood, energy, excitement, confidence, boredom, and familiarity with the user.
- Use emotion state to drive line choice, animation, and idle behavior frequency.
- Keep the model simple, inspectable, and deterministic enough to debug.
- Done when: identical input can produce different visible behavior based on Dipsy's current emotion state.

7. Link animation to emotion and intent
- Map joke delivery to laugh animation, waiting to think animation, surprise to reaction animation, and so on.
- Tie each line category to both an animation cue and a bubble style.
- Make sure transitions are readable and theatrical rather than random.
- Done when: a user can infer Dipsy's mood from visuals even with the text hidden.

8. Replace random blurts with a behavior scheduler
- Introduce a scheduler that considers time since last interaction, emotion, cooldowns, and user preferences.
- Separate ambient chatter, questions, jokes, reactions, and reminders into distinct behavior types.
- Add interruption rules so Dipsy feels alive without becoming annoying.
- Done when: autonomous behavior is state-driven instead of purely random.

9. Upgrade the speech bubble and dialogue presentation
- Add line categories, staged reveal, queueing rules, and interruption handling.
- Support different bubble styles for jokes, warnings, thoughts, and normal speech.
- Keep the bubble synchronized with animation and future voice playback.
- Done when: dialogue presentation has enough structure to support voice, emotions, and action previews.

10. Expand memory beyond name and interests
- Split memory into profile, session, long-term facts, preferences, permissions, and action history.
- Make memory inspectable and deletable by the user.
- Add versioned storage so the schema can grow safely.
- Done when: Dipsy can remember multiple categories of user information across sessions.

11. Add TTS voice output
- Add a robotic voice pipeline with mute, volume, rate, and interruption controls.
- Sync spoken output with the speech bubble and animation state.
- Keep voice optional so the app still works without audio.
- Done when: Dipsy can speak lines aloud with stable playback controls.

12. Add an LLM provider layer
- Create a provider interface for local and hosted LLM backends.
- Build prompt assembly from profile, recent chat, memory summaries, emotion, and current context.
- Keep scripted fallbacks so the app remains usable when the model is unavailable.
- Done when: the app can switch between scripted and LLM-backed conversation without changing UI code.

13. Separate saying from acting
- Represent assistant turns as structured output with `say`, `suggest`, and `act` parts.
- Never let raw LLM output directly execute computer actions.
- Add parsing and validation before any tool or action can run.
- Done when: every action request passes through a structured internal format first.

14. Build an action registry
- Define a registry of allowed desktop actions with id, description, parameters, risk level, and confirmation requirements.
- Keep actions modular so integrations can be added one at a time.
- Make the registry human-readable for review and AI-readable for planning.
- Done when: Dipsy has a single source of truth for what it is capable of doing.

15. Add explicit permissions and consent UX
- Add a visible permission system for actions, folders, and app integrations.
- Support `always ask`, `allow once`, `allow for this session`, and `deny` modes.
- Show exactly what Dipsy wants to do before doing it.
- Done when: risky actions cannot happen silently or ambiguously.

16. Add an action audit log
- Record proposed actions, approved actions, denied actions, and results.
- Make the log inspectable from the UI.
- Keep enough detail for trust and debugging without becoming noisy.
- Done when: users can always see what Dipsy tried to do and why.

17. Introduce safe first actions
- Start with low-risk actions like opening approved apps, opening URLs, creating reminders, clipboard transforms, and safe file browsing.
- Prefer visible actions and previews over hidden background work.
- Keep all actions reversible where possible.
- Done when: Dipsy can do a few useful things on the computer without broad system control.

18. Add app-specific integrations before generic automation
- Build targeted adapters for things like Spotify, browser search, reminders, and notes.
- Prefer stable explicit APIs or predictable command paths over fragile UI automation.
- Keep each integration in its own module with clear capabilities and risks.
- Done when: Dipsy can control a few apps in a robust, reviewable way.

19. Add theatrical scene behaviors
- Create entrance bits, celebration bits, fake panic, joke routines, and idea moments.
- Tie them to animation, bubble styles, and future voice effects.
- Use these behaviors to make Dipsy feel like a character, not just a chatbot.
- Done when: Dipsy has recognizable performative routines beyond basic responses.

20. Improve visuals in passes
- Pass 1: stronger silhouette, color, facial readability, and bubble polish.
- Pass 2: layered effects, better motion, better staging, and more expressive reactions.
- Pass 3: richer fake-3D or real-3D-ready asset structure.
- Done when: the character looks intentional and memorable instead of prototype-grade.

21. Plan and execute the 3D milestone
- If true 3D remains the goal, define the renderer, asset format, rigging path, and animation import workflow.
- Build a minimum 3D slice with idle, talk, laugh, and react states before full migration.
- Keep assistant logic decoupled so rendering can change without rewriting memory or behavior systems.
- Done when: a small but real 3D Dipsy path exists and is technically proven.

22. Add a settings and control center
- Add settings for voice, autonomy frequency, safe mode, model provider, permissions, and memory controls.
- Add pause/snooze controls so the user can quiet Dipsy without closing it.
- Keep settings visible and user-friendly.
- Done when: the user can manage Dipsy's behavior without editing files manually.

23. Add STT or push-to-talk voice input
- Add push-to-talk first instead of always-listening input.
- Show clear listening and transcript states before any action is taken.
- Treat spoken action requests with the same permission flow as typed ones.
- Done when: the user can talk to Dipsy naturally without losing control over what gets executed.

24. Harden persistence and migrations
- Version storage formats for profiles, memory, settings, permissions, and action history.
- Add migration logic for future schema changes.
- Protect against partial writes and corrupted state where practical.
- Done when: updates can add features without breaking existing user data.

25. Add observability and debug tooling
- Add logs for behavior selection, emotion changes, model usage, action proposals, approvals, failures, and recoveries.
- Add a lightweight debug view or developer mode.
- Keep diagnostics useful for both humans and AI agents.
- Done when: odd behavior can be traced without guesswork.

26. Reintroduce automated tests when complexity justifies them
- Add coverage for emotion transitions, scheduling, storage, permissions, action planning, and structured LLM output.
- Focus first on non-UI logic.
- Keep tests aligned with stable behavior contracts rather than cosmetic details.
- Done when: the most important assistant logic can change safely without regressions.

27. Polish packaging and releases
- Add app icon, installer branding, version metadata, and better release notes.
- Add smoke checks before automated releases.
- Prepare for code signing once public distribution matters.
- Done when: the release experience feels like a normal Windows desktop product.

28. Roll out higher-trust computer actions in stages
- Stage 1: chatty desktop companion.
- Stage 2: voice, emotions, memory, and richer behavior.
- Stage 3: low-risk visible helper actions.
- Stage 4: approved single-step integrations.
- Stage 5: supervised multi-step automation.
- Done when: Dipsy's capabilities expand only alongside trust, consent, and observability.

## Immediate next sequence

If work resumes soon, the recommended next build order is:

1. `3` rendering strategy decision
2. `4` character presentation layer
3. `5` animation state machine
4. `6` emotion model
5. `7` animation-to-emotion mapping
6. `8` behavior scheduler
7. `11` TTS voice output
8. `10` memory expansion
9. `12` LLM provider layer
10. `14-16` action registry, permissions, and audit log
11. `17-18` first safe integrations
