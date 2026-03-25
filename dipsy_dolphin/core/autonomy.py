from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable

from .models import SessionState, normalize_autonomy_pace


SPEAKING_AUTONOMY_MODES = {"quip", "question", "joke"}
DEFAULT_AUTONOMY_DELAY_MS = 12_000
DISABLED_AUTONOMY_DELAY_MS = 30_000
MIN_SCHEDULE_DELAY_MS = 1_000
ONBOARDING_RETRY_DELAY_MS = 1_500
USER_QUIET_WINDOW_MS = 12_000
PACE_DELAY_MULTIPLIERS = {
    "quiet": 1.4,
    "normal": 1.0,
    "lively": 0.75,
}


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


@dataclass(frozen=True)
class ScheduleDecision:
    should_run: bool
    next_delay_ms: int
    plan: AutonomyPlan | None = None
    reason: str = ""


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


def schedule_autonomy(
    state: SessionState,
    now_ms: int,
    *,
    rng: random.Random | None = None,
) -> ScheduleDecision:
    if not state.onboarding_complete:
        return ScheduleDecision(
            should_run=False,
            next_delay_ms=ONBOARDING_RETRY_DELAY_MS,
            reason="onboarding_incomplete",
        )

    if not state.profile.autonomy_enabled:
        return ScheduleDecision(
            should_run=False,
            next_delay_ms=DISABLED_AUTONOMY_DELAY_MS,
            reason="autonomy_disabled",
        )

    pace = normalize_autonomy_pace(state.profile.autonomy_pace)
    global_ready_at = _global_ready_at(state, pace)
    seconds_since_user = _seconds_since_user_interaction(state, now_ms)

    eligible_plans: list[AutonomyPlan] = []
    soonest_ready_at: int | None = global_ready_at if global_ready_at > now_ms else None
    for plan in AUTONOMY_PLAN_LIBRARY:
        ready_at = _plan_ready_at(
            state,
            plan,
            global_ready_at=global_ready_at,
            seconds_since_user_interaction=seconds_since_user,
            pace=pace,
        )
        if ready_at <= now_ms:
            eligible_plans.append(plan)
            continue
        soonest_ready_at = _earlier_time(soonest_ready_at, ready_at)

    if not eligible_plans:
        return ScheduleDecision(
            should_run=False,
            next_delay_ms=_delay_until(now_ms, soonest_ready_at),
            reason="cooldown",
        )

    plan = choose_autonomy_plan(state, now_ms, plans=eligible_plans, rng=rng)
    return ScheduleDecision(
        should_run=True,
        next_delay_ms=_scale_delay_ms(plan.minimum_cooldown_ms, pace),
        plan=plan,
        reason=plan.mode,
    )


def choose_autonomy_plan(
    state: SessionState,
    now_ms: int,
    *,
    plans: Iterable[AutonomyPlan] | None = None,
    rng: random.Random | None = None,
) -> AutonomyPlan:
    chooser = rng or random
    candidate_plans = tuple(AUTONOMY_PLAN_LIBRARY if plans is None else plans)
    if not candidate_plans:
        return AUTONOMY_PLAN_LIBRARY[0]

    recent_behaviors = state.recent_autonomous_behaviors[-4:]
    speaking_recent = sum(behavior in SPEAKING_AUTONOMY_MODES for behavior in recent_behaviors)
    seconds_since_user = _seconds_since_user_interaction(state, now_ms)
    emotion = state.emotion.bounded()

    weighted_plans: list[tuple[int, AutonomyPlan]] = []
    for plan in candidate_plans:
        weight = plan.base_weight

        if emotion.boredom >= 65:
            if plan.mode == "roam":
                weight += 10 if emotion.energy >= 50 else 4
            if plan.mode == "quip":
                weight += 6
            if plan.mode == "idle":
                weight = max(1, weight // 2)

        if emotion.energy <= 35:
            if plan.mode in SPEAKING_AUTONOMY_MODES or plan.mode == "roam":
                weight = max(1, weight // 2)
            if plan.mode in {"idle", "emote"}:
                weight += 6

        if emotion.excitement >= 65:
            if plan.mode == "joke":
                weight += 3
            if plan.mode == "quip":
                weight += 4

        if emotion.confidence <= 35 and plan.mode in {"question", "joke"}:
            weight = max(1, weight // 3)

        if emotion.familiarity >= 55 and plan.mode in {"quip", "question"}:
            weight += 3
        elif emotion.familiarity <= 20 and plan.mode == "question":
            weight = max(1, weight // 2)

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
        return candidate_plans[0]

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


def _plan_ready_at(
    state: SessionState,
    plan: AutonomyPlan,
    *,
    global_ready_at: int,
    seconds_since_user_interaction: int | None,
    pace: str,
) -> int:
    ready_at = global_ready_at
    ready_at = max(ready_at, _user_quiet_ready_at(state, pace))

    last_plan_at_ms = state.autonomous_behavior_times_ms.get(plan.mode, 0)
    ready_at = max(
        ready_at, _ready_at(last_plan_at_ms, _scale_delay_ms(plan.minimum_cooldown_ms, pace))
    )

    if plan.min_seconds_since_user > 0 and seconds_since_user_interaction is not None:
        ready_at = max(
            ready_at,
            state.last_user_interaction_ms + (plan.min_seconds_since_user * 1000),
        )

    return ready_at


def _global_ready_at(state: SessionState, pace: str) -> int:
    if state.last_autonomous_at_ms <= 0:
        return 0
    base_delay_ms = max(DEFAULT_AUTONOMY_DELAY_MS, state.autonomy_cooldown_ms)
    return _ready_at(state.last_autonomous_at_ms, _scale_delay_ms(base_delay_ms, pace))


def _user_quiet_ready_at(state: SessionState, pace: str) -> int:
    return _ready_at(state.last_user_interaction_ms, _scale_delay_ms(USER_QUIET_WINDOW_MS, pace))


def _ready_at(last_event_ms: int, delay_ms: int) -> int:
    if last_event_ms <= 0:
        return 0
    return last_event_ms + max(MIN_SCHEDULE_DELAY_MS, delay_ms)


def _scale_delay_ms(delay_ms: int, pace: str) -> int:
    multiplier = PACE_DELAY_MULTIPLIERS[normalize_autonomy_pace(pace)]
    scaled = int(delay_ms * multiplier)
    return max(MIN_SCHEDULE_DELAY_MS, scaled)


def _delay_until(now_ms: int, ready_at_ms: int | None) -> int:
    if ready_at_ms is None or ready_at_ms <= now_ms:
        return DEFAULT_AUTONOMY_DELAY_MS
    return max(MIN_SCHEDULE_DELAY_MS, ready_at_ms - now_ms)


def _earlier_time(current: int | None, candidate: int) -> int:
    if current is None:
        return candidate
    return min(current, candidate)


def _seconds_since_user_interaction(state: SessionState, now_ms: int) -> int | None:
    if state.last_user_interaction_ms <= 0:
        return None
    elapsed_ms = max(0, now_ms - state.last_user_interaction_ms)
    return elapsed_ms // 1000
