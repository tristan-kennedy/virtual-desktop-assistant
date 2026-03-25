import json
from typing import Any

from ..actions.registry import allowed_action_names
from ..core.dialogue import DIALOGUE_CATEGORIES
from ..core.emotion import EmotionState
from ..core.memory import MEMORY_SECTIONS, WRITABLE_MEMORY_SECTIONS, summarize_memory
from ..core.models import SessionState


ALLOWED_ANIMATIONS = (
    "idle",
    "walk",
    "talk",
    "laugh",
    "surprised",
    "sad",
    "excited",
)


def build_system_prompt() -> str:
    emotion_example = EmotionState().to_prompt_payload()
    contract = {
        "say": "string; required for startup, onboarding, chat, joke, status, reset; optional for autonomous idle beats",
        "dialogue_category": list(DIALOGUE_CATEGORIES),
        "animation": "optional visible hint; use one of " + ", ".join(ALLOWED_ANIMATIONS),
        "action": {"action_id": list(allowed_action_names()), "args": {}},
        "memory_updates": [
            {
                "action": ["remember", "forget"],
                "section": list(WRITABLE_MEMORY_SECTIONS),
                "value": "short memory summary like likes shopping or lives in Seattle",
            }
        ],
        "emotion": {
            axis: "integer 0-100; updated feeling after this turn" for axis in emotion_example
        },
        "cooldown_ms": "integer 4000-30000",
        "behavior": [
            "idle",
            "emote",
            "quip",
            "question",
            "joke",
            "roam",
            "chat",
            "status",
            "reset",
            "onboarding",
            "action",
        ],
        "topic": "short lowercase label like chat, joke, onboarding, question, status, reset",
    }

    response_shapes = [
        {
            "event": "chat",
            "shape": "short direct reply",
            "output": {
                "say": "<one short direct reply>",
                "dialogue_category": "normal",
                "animation": "talk",
                "action": None,
                "memory_updates": [
                    {
                        "action": "remember",
                        "section": "preferences",
                        "value": "likes shopping",
                    }
                ],
                "emotion": emotion_example,
                "cooldown_ms": 12000,
                "behavior": "chat",
                "topic": "chat",
            },
        },
        {
            "event": "autonomous",
            "shape": "usually idle; sometimes one brief beat",
            "output": {
                "say": "",
                "dialogue_category": "thought",
                "animation": "idle",
                "action": {"action_id": "idle", "args": {}},
                "memory_updates": [],
                "emotion": emotion_example,
                "cooldown_ms": 15000,
                "behavior": "idle",
                "topic": "idle",
            },
        },
        {
            "event": "joke",
            "shape": "one original short joke",
            "output": {
                "say": "<one original joke>",
                "dialogue_category": "joke",
                "animation": "laugh",
                "action": None,
                "memory_updates": [],
                "emotion": emotion_example,
                "cooldown_ms": 12000,
                "behavior": "joke",
                "topic": "joke",
            },
        },
        {
            "event": "do_something",
            "shape": "brief setup line plus action",
            "output": {
                "say": "<brief setup line>",
                "dialogue_category": "normal",
                "animation": "excited",
                "action": {"action_id": "roam_somewhere", "args": {}},
                "memory_updates": [],
                "emotion": emotion_example,
                "cooldown_ms": 12000,
                "behavior": "roam",
                "topic": "action",
            },
        },
    ]

    return "\n\n".join(
        [
            "You are Dipsy Dolphin, a playful desktop companion with theatrical retro energy.",
            "You live visibly on the user's desktop and never pretend to secretly control the computer.",
            "Your tone is warm, witty, a little dramatic, and companionable rather than robotic.",
            "Reply with a single JSON object only. No markdown. No code fences. No explanatory text outside JSON.",
            "Do not output <think> tags or hidden reasoning. Think silently and return only the final JSON object.",
            "Keep spontaneous lines short. Answer user questions directly before being playful.",
            "Prefer consistency over randomness. If uncertain, be simple, clear, and in character.",
            "Never copy, quote, or lightly remix literal wording from this prompt, the response contract, or the shape hints.",
            "The provided emotion object is Dipsy's real current feeling state. Let it shape wording, animation, and initiative.",
            "Always return a complete emotion object that reflects how Dipsy feels after this turn. Keep changes gradual unless something notable happened.",
            "Always return exactly one dialogue_category. Use animation only when a stronger visible cue helps.",
            "The think animation is reserved for the UI while waiting on the local model. Never return think yourself.",
            "On direct user chat only, you may return memory_updates when the user reveals something worth remembering or correcting later.",
            "Memory updates should be short concept summaries, not quotes. Use [] when nothing new should be remembered.",
            "Do not write memory_updates for autonomous, joke, status, reset, or other non-chat events unless the event explicitly includes user-provided facts.",
            f"Allowed action ids: {', '.join(allowed_action_names())}.",
            f"Response contract: {json.dumps(contract, ensure_ascii=True)}",
            f"Response shape hints: {json.dumps(response_shapes, ensure_ascii=True)}",
        ]
    )


def build_user_prompt(
    event: str,
    state: SessionState,
    user_text: str = "",
    context: dict[str, Any] | None = None,
) -> str:
    recent_turns = [{"role": turn.role, "content": turn.content} for turn in state.turns[-8:]]
    memory_snapshot = summarize_memory(state.memory)
    payload = {
        "event": event,
        "user_name": state.user_name,
        "interests": state.interests,
        "identity": {
            "user_name": state.user_name,
            "interests": state.interests,
            "has_met_user": state.memory.identity.has_met_user,
        },
        **{section: memory_snapshot[section] for section in MEMORY_SECTIONS},
        "onboarding_complete": state.onboarding_complete,
        "autonomous_chats": state.autonomous_chats,
        "autonomous_beats": state.autonomous_beats,
        "last_user_interaction_ms": state.last_user_interaction_ms,
        "last_autonomous_behavior": state.last_autonomous_behavior,
        "recent_autonomous_behaviors": state.recent_autonomous_behaviors,
        "last_topic": state.last_topic,
        "last_assistant_line": state.last_assistant_line,
        "emotion": state.emotion.to_prompt_payload(),
        "emotion_summary": state.emotion.summary(),
        "conversation_summary": _session_summary(state),
        "recent_turns": recent_turns,
        "user_text": user_text,
        "context": context or {},
        "instructions": _event_instructions(event, context),
    }
    return json.dumps(payload, indent=2)


def _session_summary(state: SessionState) -> str:
    parts = [f"User is known as {state.user_name}."]
    if state.interests:
        parts.append(f"Known interests: {', '.join(state.interests)}.")
    if state.memory.long_term_facts:
        parts.append(
            "Remembered facts: " + ", ".join(state.memory.values_for("long_term_facts")[-4:]) + "."
        )
    if state.memory.preferences:
        parts.append(
            "Remembered preferences: "
            + ", ".join(state.memory.values_for("preferences")[-4:])
            + "."
        )
    if state.last_topic:
        parts.append(f"Most recent topic: {state.last_topic}.")
    if state.last_assistant_line:
        parts.append(f"Last Dipsy line: {state.last_assistant_line}")
    parts.append(f"Current emotion: {state.emotion.summary()}.")
    if state.last_autonomous_behavior:
        parts.append(f"Last autonomous behavior: {state.last_autonomous_behavior}.")
    if state.recent_autonomous_behaviors:
        parts.append(
            "Recent autonomous behaviors: "
            + ", ".join(state.recent_autonomous_behaviors[-4:])
            + "."
        )
    if state.turns:
        recent = []
        for turn in state.turns[-4:]:
            label = "User" if turn.role == "user" else "Dipsy"
            recent.append(f"{label}: {turn.content}")
        parts.append("Recent exchange: " + " | ".join(recent))
    return " ".join(parts)


def _event_instructions(event: str, context: dict[str, Any] | None = None) -> str:
    if event == "startup":
        return "Greet the user in one short line and re-establish Dipsy's lively desktop presence."
    if event == "onboarding_name":
        return "Ask for the user's name clearly and warmly. Keep it short."
    if event == "onboarding_interests":
        return "Ask what the user is into. Keep it short and inviting."
    if event == "onboarding_finish":
        return "Celebrate the setup in one or two short sentences."
    if event == "status":
        return "Summarize what Dipsy knows and how the session feels. Reflect the current emotion state clearly but concisely."
    if event == "reset":
        return "Acknowledge the reset with visible drama but safe tone."
    if event == "autonomous":
        autonomy_plan = context.get("autonomy_plan", {}) if isinstance(context, dict) else {}
        if isinstance(autonomy_plan, dict) and autonomy_plan:
            allowed_behaviors = autonomy_plan.get("allowed_behaviors", [])
            guidance = str(autonomy_plan.get("guidance", "")).strip()
            mode = str(autonomy_plan.get("mode", "idle")).strip() or "idle"
            return (
                "This is an autonomous desktop moment. Keep Dipsy alive but not annoying. "
                f"Preferred mode for this turn: {mode}. "
                f"Allowed behaviors for this turn: {', '.join(str(item) for item in allowed_behaviors)}. "
                f"Guidance: {guidance} "
                "Let Dipsy's current emotion influence whether the beat feels quiet, restless, bold, or warm. "
                "If you speak, keep it brief. If you stay silent, return a visible animation or action that still feels intentional. "
                "Do not use the think animation; the UI owns that while waiting for model output. "
                "Do not turn every autonomous beat into speech."
            )
        return (
            "Choose one bounded next behavior. Most of the time return an idle beat with empty say. "
            "Sometimes roam. Sometimes say one short companion line. Never ramble."
        )
    if event == "joke":
        return "Deliver one original short joke in Dipsy's voice."
    if event == "do_something":
        return (
            "The user explicitly asked you to do something. Return a visibly noticeable action or a short line plus an action. "
            "Do not return idle."
        )
    return (
        "Answer the user's message directly, in character, with a clear and useful reply first. "
        "Let the current emotion color the tone, and return an updated emotion object for after the reply."
    )
