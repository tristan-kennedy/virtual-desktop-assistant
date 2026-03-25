import random

from dipsy_dolphin.core.autonomy import choose_autonomy_plan, schedule_autonomy
from dipsy_dolphin.core.emotion import EmotionState
from dipsy_dolphin.core.models import SessionState, UserProfile


def test_schedule_autonomy_waits_after_recent_user_interaction() -> None:
    state = SessionState(
        profile=UserProfile(user_name="Taylor", has_met_user=True),
        last_user_interaction_ms=50_000,
    )

    decision = schedule_autonomy(state, 55_000)

    assert decision.should_run is False
    assert decision.next_delay_ms == 7_000


def test_schedule_autonomy_uses_per_behavior_cooldowns() -> None:
    state = SessionState(
        profile=UserProfile(user_name="Taylor", has_met_user=True),
        autonomous_behavior_times_ms={
            "idle": 120_000,
            "emote": 120_000,
            "quip": 120_000,
            "roam": 120_000,
            "question": 120_000,
            "joke": 120_000,
        },
    )

    decision = schedule_autonomy(state, 125_000)

    assert decision.should_run is False
    assert decision.next_delay_ms == 5_000


def test_schedule_autonomy_respects_pace_preference() -> None:
    quiet_state = SessionState(
        profile=UserProfile(user_name="Taylor", has_met_user=True, autonomy_pace="quiet"),
        last_user_interaction_ms=50_000,
    )
    lively_state = SessionState(
        profile=UserProfile(user_name="Taylor", has_met_user=True, autonomy_pace="lively"),
        last_user_interaction_ms=50_000,
    )

    quiet = schedule_autonomy(quiet_state, 55_000)
    lively = schedule_autonomy(lively_state, 55_000)

    assert quiet.next_delay_ms > lively.next_delay_ms


def test_schedule_autonomy_can_run_when_state_is_ready() -> None:
    state = SessionState(profile=UserProfile(user_name="Taylor", has_met_user=True))

    decision = schedule_autonomy(state, 120_000)

    assert decision.should_run is True
    assert decision.plan is not None


def test_high_boredom_biases_roam_more_often_than_baseline() -> None:
    baseline_state = SessionState(profile=UserProfile(user_name="Taylor", has_met_user=True))
    bored_state = SessionState(
        profile=UserProfile(user_name="Taylor", has_met_user=True),
        emotion=EmotionState(boredom=82, energy=78, excitement=40),
    )

    baseline_rng = random.Random(7)
    bored_rng = random.Random(7)
    baseline_roams = sum(
        choose_autonomy_plan(baseline_state, 120_000, rng=baseline_rng).mode == "roam"
        for _ in range(250)
    )
    bored_roams = sum(
        choose_autonomy_plan(bored_state, 120_000, rng=bored_rng).mode == "roam" for _ in range(250)
    )

    assert bored_roams > baseline_roams


def test_low_energy_biases_quiet_modes_more_often_than_high_energy() -> None:
    low_energy_state = SessionState(
        profile=UserProfile(user_name="Taylor", has_met_user=True),
        emotion=EmotionState(energy=18, boredom=30, confidence=50),
    )
    high_energy_state = SessionState(
        profile=UserProfile(user_name="Taylor", has_met_user=True),
        emotion=EmotionState(energy=82, boredom=30, confidence=50),
    )

    low_energy_rng = random.Random(11)
    high_energy_rng = random.Random(11)
    low_energy_quiet = sum(
        choose_autonomy_plan(low_energy_state, 120_000, rng=low_energy_rng).mode
        in {"idle", "emote"}
        for _ in range(250)
    )
    high_energy_quiet = sum(
        choose_autonomy_plan(high_energy_state, 120_000, rng=high_energy_rng).mode
        in {"idle", "emote"}
        for _ in range(250)
    )

    assert low_energy_quiet > high_energy_quiet
