from __future__ import annotations

import random
from dataclasses import dataclass

from .models import SessionState


SPEAKING_AUTONOMY_MODES = {"quip", "question", "joke"}


@dataclass(frozen=True)
class AutonomyPlan:
    mode: str
    allowed_behaviors: tuple[str, ...]
    guidance: str
    minimum_cooldown_ms: int
    base_weight: int
    min_seconds_since_user: int = 0

    def prompt_payload(self, *, seconds_since_user_interaction: int | None) -> dict[str, object]:
        return {
            "mode": self.mode,
            "allowed_behaviors": list(self.allowed_behaviors),
            "guidance": self.guidance,
            "minimum_cooldown_ms": self.minimum_cooldown_ms,
            "seconds_since_user_interaction": seconds_since_user_interaction,
        }


AUTONOMY_PLAN_LIBRARY: tuple[AutonomyPlan, ...] = (
    AutonomyPlan(
        mode="idle",
        allowed_behaviors=("idle", "emote"),
        guidance="Prefer silence. Usually return an empty say with idle or a tiny silent emote.",
        minimum_cooldown_ms=12000,
        base_weight=56,
    ),
    AutonomyPlan(
        mode="emote",
        allowed_behaviors=("emote",),
        guidance="Return a silent visible beat. No speech. No roaming. Use a brief nonverbal animation.",
        minimum_cooldown_ms=10000,
        base_weight=22,
    ),
    AutonomyPlan(
        mode="quip",
        allowed_behaviors=("quip",),
        guidance="Say one short companion line. Keep it to 4-10 words and do not ask a question.",
        minimum_cooldown_ms=18000,
        base_weight=12,
        min_seconds_since_user=25,
    ),
    AutonomyPlan(
        mode="roam",
        allowed_behaviors=("roam", "emote"),
        guidance="Move somewhere on screen. An optional setup line is fine, but keep it very short.",
        minimum_cooldown_ms=22000,
        base_weight=8,
        min_seconds_since_user=18,
    ),
    AutonomyPlan(
        mode="question",
        allowed_behaviors=("question",),
        guidance="Ask one tiny playful question. Keep it brief and easy to ignore.",
        minimum_cooldown_ms=26000,
        base_weight=5,
        min_seconds_since_user=45,
    ),
    AutonomyPlan(
        mode="joke",
        allowed_behaviors=("joke",),
        guidance="Tell one short original joke. Keep it to one sentence.",
        minimum_cooldown_ms=32000,
        base_weight=3,
        min_seconds_since_user=60,
    ),
)


def choose_autonomy_plan(
    state: SessionState,
    now_ms: int,
    *,
    rng: random.Random | None = None,
) -> AutonomyPlan:
    chooser = rng or random
    recent_behaviors = state.recent_autonomous_behaviors[-4:]
    speaking_recent = sum(behavior in SPEAKING_AUTONOMY_MODES for behavior in recent_behaviors)
    seconds_since_user = _seconds_since_user_interaction(state, now_ms)

    weighted_plans: list[tuple[int, AutonomyPlan]] = []
    for plan in AUTONOMY_PLAN_LIBRARY:
        weight = plan.base_weight

        if seconds_since_user is not None and seconds_since_user < plan.min_seconds_since_user:
            if plan.mode in SPEAKING_AUTONOMY_MODES or plan.mode == "roam":
                weight = 0
            else:
                weight = max(1, weight // 3)

        if state.last_autonomous_behavior == plan.mode:
            weight = max(1, weight // 5)

        repeat_count = recent_behaviors.count(plan.mode)
        if repeat_count:
            weight = max(1, weight // (1 + repeat_count * 2))

        if plan.mode in SPEAKING_AUTONOMY_MODES and speaking_recent >= 2:
            weight = max(1, weight // 4)

        if plan.mode == "roam" and recent_behaviors[-2:].count("roam"):
            weight = max(1, weight // 6)

        if weight > 0:
            weighted_plans.append((weight, plan))

    if not weighted_plans:
        return AUTONOMY_PLAN_LIBRARY[0]

    total_weight = sum(weight for weight, _plan in weighted_plans)
    roll = chooser.uniform(0, total_weight)
    running_total = 0.0
    for weight, plan in weighted_plans:
        running_total += weight
        if roll <= running_total:
            return plan
    return weighted_plans[-1][1]


def seconds_since_user_interaction(state: SessionState, now_ms: int) -> int | None:
    return _seconds_since_user_interaction(state, now_ms)


def _seconds_since_user_interaction(state: SessionState, now_ms: int) -> int | None:
    if state.last_user_interaction_ms <= 0:
        return None
    elapsed_ms = max(0, now_ms - state.last_user_interaction_ms)
    return elapsed_ms // 1000
