import json
from typing import Any

from ..actions.registry import allowed_action_names
from ..core.models import SessionState


ALLOWED_ANIMATIONS = (
    "idle",
    "walk",
    "talk",
    "think",
    "laugh",
    "surprised",
    "sad",
    "excited",
)


def build_system_prompt() -> str:
    contract = {
        "say": "string; required for startup, onboarding, chat, joke, status, reset; optional for autonomous idle beats",
        "animation": list(ALLOWED_ANIMATIONS),
        "speech_style": ["normal", "joke", "question", "spark", "alert", "status", "onboarding"],
        "action": {"action_id": list(allowed_action_names()), "args": {}},
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
                "animation": "talk",
                "speech_style": "normal",
                "action": None,
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
                "animation": "idle",
                "speech_style": "normal",
                "action": {"action_id": "idle", "args": {}},
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
                "animation": "laugh",
                "speech_style": "joke",
                "action": None,
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
                "animation": "excited",
                "speech_style": "normal",
                "action": {"action_id": "roam_somewhere", "args": {}},
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
    payload = {
        "event": event,
        "user_name": state.user_name,
        "interests": state.interests,
        "onboarding_complete": state.onboarding_complete,
        "autonomous_chats": state.autonomous_chats,
        "autonomous_beats": state.autonomous_beats,
        "last_user_interaction_ms": state.last_user_interaction_ms,
        "last_autonomous_behavior": state.last_autonomous_behavior,
        "recent_autonomous_behaviors": state.recent_autonomous_behaviors,
        "last_topic": state.last_topic,
        "last_assistant_line": state.last_assistant_line,
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
    if state.last_topic:
        parts.append(f"Most recent topic: {state.last_topic}.")
    if state.last_assistant_line:
        parts.append(f"Last Dipsy line: {state.last_assistant_line}")
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
        return "Summarize what Dipsy knows and how the session feels. Be specific and concise."
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
                "If you speak, keep it brief. If you stay silent, return a visible animation or action that still feels intentional. "
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
    return "Answer the user's message directly, in character, with a clear and useful reply first."
