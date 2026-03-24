from dipsy_dolphin.core.autonomy import choose_autonomy_plan
from dipsy_dolphin.core.models import SessionState


def test_autonomy_plan_stays_quiet_immediately_after_user_interaction() -> None:
    state = SessionState(last_user_interaction_ms=50_000)

    plan = choose_autonomy_plan(state, 55_000)

    assert plan.mode in {"idle", "emote"}
