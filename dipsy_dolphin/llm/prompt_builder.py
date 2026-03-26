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
        "say": "string; required for startup, onboarding, chat, joke, status, reset; optional for inactivity ticks",
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
        "cooldown_ms": "integer 4000-120000",
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
            "event": "chat",
            "shape": "clear closing intent may reply briefly and quit",
            "output": {
                "say": "<one short goodbye line>",
                "dialogue_category": "normal",
                "animation": "talk",
                "action": {"action_id": "quit_app", "args": {}},
                "memory_updates": [],
                "emotion": emotion_example,
                "cooldown_ms": 4000,
                "behavior": "action",
                "topic": "goodbye",
            },
        },
        {
            "event": "inactive_tick",
            "shape": "brief optional response after user inactivity",
            "output": {
                "say": "",
                "dialogue_category": "thought",
                "animation": "idle",
                "action": None,
                "memory_updates": [],
                "emotion": emotion_example,
                "cooldown_ms": 25000,
                "behavior": "idle",
                "topic": "inactivity",
            },
        },
        {
            "event": "action_result",
            "shape": "brief follow-up after a function already ran; may request one next action if still needed",
            "output": {
                "say": "<short follow-up that reacts to the real function result>",
                "dialogue_category": "normal",
                "animation": "talk",
                "action": {"action_id": "roam_somewhere", "args": {}},
                "memory_updates": [],
                "emotion": emotion_example,
                "cooldown_ms": 12000,
                "behavior": "action",
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
            "Chat is the main way the user should ask for jokes, movement, status, and other supported routines.",
            "App-level actions also happen through chat. If the user clearly asks Dipsy to leave, close, quit, or go away now, you may use quit_app.",
            "Do not use quit_app for casual sign-offs unless the user is clearly asking to close Dipsy itself.",
            "Inactivity ticks are neutral opportunities after quiet time, not pre-scripted behavior requests.",
            "During inactivity, prioritize variety across beats instead of repeating one pattern.",
            "Do not default to leading questions about interests or repeatedly probe the user for more facts during inactivity.",
            "Use recent_autonomous_behaviors, recent_turns, and the current emotion state to vary between silence, quips, jokes, visible emotes, and allowed actions when appropriate.",
            "Longer quiet stretches are good. After a noticeable beat, you may return a much longer cooldown_ms to let the desktop stay calm.",
            "If a user asks for something that matches an allowed action, decide yourself whether to answer directly, use an action, or do both.",
            "On direct user chat only, you may return memory_updates when the user reveals something worth remembering or correcting later.",
            "Memory updates should be short concept summaries, not quotes. Use [] when nothing new should be remembered.",
            "Do not write memory_updates for inactivity ticks, joke, status, reset, or other non-chat events unless the event explicitly includes user-provided facts.",
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
    if event == "inactive_tick":
        seconds_since_user = ""
        cooldown_remaining = ""
        if isinstance(context, dict):
            seconds_since_user = str(context.get("seconds_since_user_interaction", "")).strip()
            cooldown_remaining = str(context.get("cooldown_remaining_ms", "")).strip()
        return (
            "The user has been inactive for a while. Decide whether to stay silent, speak briefly, or use one allowed action. "
            f"Seconds since user interaction: {seconds_since_user or 'unknown'}. "
            f"Current inactivity cooldown remaining before this tick fired: {cooldown_remaining or '0'} ms. "
            "Prioritize diversity across beats and avoid repeatedly steering back to the user's interests unless there is a strong reason in the recent context. "
            "It is often better to stay silent, give a tiny quip, tell a small joke, or do a visible action than to ask another leading question. "
            "Longer cooldowns are fine after a bigger beat. "
            "Keep the beat bounded and visible if you choose to do something. "
            "Do not use the think animation; the UI owns that while waiting for model output."
        )
    if event == "joke":
        return "Deliver one original short joke in Dipsy's voice."
    if event == "do_something":
        return (
            "The user explicitly asked you to do something. Return a visibly noticeable action or a short line plus an action. "
            "Do not return idle."
        )
    if event == "action_result":
        return (
            "A function already ran. Use context.latest_execution and context.loop_steps as real runtime feedback. "
            "If the task is complete, return the final user-facing follow-up with no action. "
            "If one more allowed action is clearly needed, return exactly one next action. "
            "Do not repeat the same failed action unless the latest execution shows a good reason to retry."
        )
    return (
        "Answer the user's message directly, in character, with a clear and useful reply first. "
        "Let the current emotion color the tone, and return an updated emotion object for after the reply. "
        "If the user asks for something Dipsy can do, you may return an action instead of hardcoded chat-only behavior."
    )
