from __future__ import annotations

from dataclasses import dataclass

from .models import SessionState, normalize_autonomy_pace


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
class ScheduleDecision:
    should_run: bool
    next_delay_ms: int
    reason: str = ""
    seconds_since_user_interaction: int | None = None
    cooldown_remaining_ms: int | None = None


def schedule_autonomy(state: SessionState, now_ms: int) -> ScheduleDecision:
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
    quiet_ready_at = _user_quiet_ready_at(state, pace)
    cooldown_ready_at = _global_ready_at(state, pace)
    ready_at = max(quiet_ready_at, cooldown_ready_at)
    seconds_since_user = _seconds_since_user_interaction(state, now_ms)

    if ready_at > now_ms:
        return ScheduleDecision(
            should_run=False,
            next_delay_ms=_delay_until(now_ms, ready_at),
            reason="cooldown",
            seconds_since_user_interaction=seconds_since_user,
            cooldown_remaining_ms=max(0, ready_at - now_ms),
        )

    return ScheduleDecision(
        should_run=True,
        next_delay_ms=_scale_delay_ms(max(DEFAULT_AUTONOMY_DELAY_MS, state.autonomy_cooldown_ms), pace),
        reason="ready",
        seconds_since_user_interaction=seconds_since_user,
        cooldown_remaining_ms=0,
    )


def seconds_since_user_interaction(state: SessionState, now_ms: int) -> int | None:
    return _seconds_since_user_interaction(state, now_ms)


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


def _delay_until(now_ms: int, ready_at_ms: int) -> int:
    if ready_at_ms <= now_ms:
        return DEFAULT_AUTONOMY_DELAY_MS
    return max(MIN_SCHEDULE_DELAY_MS, ready_at_ms - now_ms)


def _seconds_since_user_interaction(state: SessionState, now_ms: int) -> int | None:
    if state.last_user_interaction_ms <= 0:
        return None
    elapsed_ms = max(0, now_ms - state.last_user_interaction_ms)
    return elapsed_ms // 1000
