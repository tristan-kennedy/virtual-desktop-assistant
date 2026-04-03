from dipsy_dolphin.core.emotion import EmotionState
from dipsy_dolphin.core.models import SessionState
from dipsy_dolphin.core.scenes import plan_scene_opportunity


def test_action_result_success_recommends_celebration() -> None:
    state = SessionState()

    scene = plan_scene_opportunity(
        "action_result",
        state,
        context={"latest_execution": {"status": "success"}},
    )

    assert scene.allowed_scene_kinds == ("celebration", "idea")
    assert scene.recommended_scene_kind == "celebration"


def test_action_result_failure_recommends_panic() -> None:
    state = SessionState()

    scene = plan_scene_opportunity(
        "action_result",
        state,
        context={"latest_execution": {"status": "failed"}},
    )

    assert scene.allowed_scene_kinds == ("panic", "idea")
    assert scene.recommended_scene_kind == "panic"


def test_scene_planner_avoids_repeating_last_two_scene_kinds() -> None:
    state = SessionState(
        recent_scene_kinds=["celebration", "panic"],
        scene_kind_times_ms={"celebration": 100, "panic": 200, "joke": 300, "idea": 50},
    )

    scene = plan_scene_opportunity("do_something", state)

    assert scene.recommended_scene_kind == "idea"


def test_inactive_scene_planner_uses_emotion_to_pick_idea() -> None:
    state = SessionState(emotion=EmotionState(boredom=80, confidence=25))

    scene = plan_scene_opportunity("inactive_tick", state)

    assert scene.allowed_scene_kinds == ("joke", "idea")
    assert scene.recommended_scene_kind == "idea"


def test_inactive_scene_planner_nudges_toward_spoken_joke_after_multiple_silent_beats() -> None:
    state = SessionState(
        emotion=EmotionState(excitement=40, familiarity=50),
        consecutive_silent_autonomous_turns=3,
    )

    scene = plan_scene_opportunity("inactive_tick", state)

    assert scene.recommended_scene_kind == "joke"
