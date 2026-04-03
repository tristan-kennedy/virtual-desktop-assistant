from __future__ import annotations

from dataclasses import dataclass, field

from .models import SessionState


SCENE_KINDS = (
    "entrance",
    "celebration",
    "panic",
    "joke",
    "idea",
)


def normalize_scene_kind(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in SCENE_KINDS:
        return cleaned
    return ""


@dataclass(frozen=True)
class SceneOpportunity:
    allowed_scene_kinds: tuple[str, ...] = ()
    recommended_scene_kind: str = ""
    reason: str = ""
    recent_scene_kinds: tuple[str, ...] = field(default_factory=tuple)

    def to_prompt_payload(self) -> dict[str, object]:
        return {
            "allowed_scene_kinds": list(self.allowed_scene_kinds),
            "recommended_scene_kind": self.recommended_scene_kind,
            "reason": self.reason,
            "recent_scene_kinds": list(self.recent_scene_kinds),
        }


def plan_scene_opportunity(
    event: str,
    state: SessionState,
    *,
    context: dict[str, object] | None = None,
) -> SceneOpportunity:
    recent_scene_kinds = tuple(state.recent_scene_kinds[-6:])
    last_two = set(recent_scene_kinds[-2:])
    allowed: tuple[str, ...] = ()
    preferred = ""
    reason = ""

    if event == "startup":
        allowed = ("entrance", "idea")
        preferred = "entrance"
        reason = "startup_presence"
    elif event == "onboarding_finish":
        allowed = ("celebration",)
        preferred = "celebration"
        reason = "onboarding_complete"
    elif event == "action_result":
        status = _latest_execution_status(context)
        if status in {"failed", "rejected"}:
            allowed = ("panic", "idea")
            preferred = "panic"
            reason = f"action_{status}"
        elif status == "success":
            allowed = ("celebration", "idea")
            preferred = "celebration"
            reason = "action_success"
    elif event == "inactive_tick":
        allowed = ("joke", "idea")
        preferred = "joke" if _prefer_joke_for_inactivity(state) else "idea"
        reason = "inactive_variety"
    elif event == "joke":
        allowed = ("joke",)
        preferred = "joke"
        reason = "joke_request"
    elif event == "do_something":
        allowed = ("celebration", "panic", "joke", "idea")
        preferred = _least_recent_allowed(state, allowed, excluded=last_two)
        reason = "playful_visible_prompt"
    elif event == "status":
        allowed = ("idea",)
        preferred = "idea" if _prefer_idea_for_status(state) else ""
        reason = "reflective_status"

    if preferred and preferred in last_two:
        preferred = _least_recent_allowed(state, allowed, excluded=last_two)

    return SceneOpportunity(
        allowed_scene_kinds=allowed,
        recommended_scene_kind=preferred,
        reason=reason,
        recent_scene_kinds=recent_scene_kinds,
    )


def _latest_execution_status(context: dict[str, object] | None) -> str:
    if not isinstance(context, dict):
        return ""
    latest_execution = context.get("latest_execution")
    if not isinstance(latest_execution, dict):
        return ""
    return str(latest_execution.get("status", "")).strip().lower()


def _prefer_joke_for_inactivity(state: SessionState) -> bool:
    emotion = state.emotion.bounded()
    if state.consecutive_silent_autonomous_turns >= 2:
        return emotion.familiarity >= 45 or emotion.excitement >= 35
    if emotion.excitement >= 45 or emotion.familiarity >= 50:
        return True
    if emotion.confidence <= 35 or emotion.boredom >= 60:
        return False
    return state.last_scene_kind != "joke"


def _prefer_idea_for_status(state: SessionState) -> bool:
    emotion = state.emotion.bounded()
    return bool(
        state.last_topic
        or state.memory.long_term_facts
        or state.memory.preferences
        or emotion.boredom >= 55
        or emotion.confidence <= 45
    )


def _least_recent_allowed(
    state: SessionState,
    allowed: tuple[str, ...],
    *,
    excluded: set[str] | None = None,
) -> str:
    excluded = excluded or set()
    candidates = [scene_kind for scene_kind in allowed if scene_kind not in excluded]
    if not candidates:
        return ""
    return min(candidates, key=lambda scene_kind: state.scene_kind_times_ms.get(scene_kind, -1))
