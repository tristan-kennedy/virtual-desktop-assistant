from dipsy_dolphin.core.autonomy import schedule_autonomy
from dipsy_dolphin.core.models import SessionState, UserProfile


def test_schedule_autonomy_waits_after_recent_user_interaction() -> None:
    state = SessionState(
        profile=UserProfile(user_name="Taylor", has_met_user=True),
        last_user_interaction_ms=50_000,
    )

    decision = schedule_autonomy(state, 55_000)

    assert decision.should_run is False
    assert decision.next_delay_ms == 7_000
    assert decision.reason == "cooldown"
    assert decision.seconds_since_user_interaction == 5
    assert decision.cooldown_remaining_ms == 7_000


def test_schedule_autonomy_respects_global_autonomy_cooldown() -> None:
    state = SessionState(
        profile=UserProfile(user_name="Taylor", has_met_user=True),
        last_autonomous_at_ms=120_000,
        autonomy_cooldown_ms=18_000,
    )

    decision = schedule_autonomy(state, 125_000)

    assert decision.should_run is False
    assert decision.next_delay_ms == 13_000
    assert decision.cooldown_remaining_ms == 13_000


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
    assert decision.reason == "ready"
    assert decision.cooldown_remaining_ms == 0


def test_schedule_autonomy_waits_during_onboarding() -> None:
    state = SessionState(
        profile=UserProfile(),
        onboarding_complete=False,
    )

    decision = schedule_autonomy(state, 120_000)

    assert decision.should_run is False
    assert decision.reason == "onboarding_incomplete"
    assert decision.next_delay_ms == 1_500


def test_schedule_autonomy_respects_disabled_setting() -> None:
    state = SessionState(
        profile=UserProfile(user_name="Taylor", has_met_user=True, autonomy_enabled=False)
    )

    decision = schedule_autonomy(state, 120_000)

    assert decision.should_run is False
    assert decision.reason == "autonomy_disabled"
    assert decision.next_delay_ms == 30_000
