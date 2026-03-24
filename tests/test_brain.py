from dipsy_dolphin.core.brain import AssistantBrain
from dipsy_dolphin.core.models import SessionState


def test_parse_interests_normalizes_and_limits_entries() -> None:
    brain = AssistantBrain()

    interests = brain.parse_interests(
        "Games, Music, coding, music, movies, books, robots, everything"
    )

    assert interests == ["games", "music", "coding", "movies", "books"]


def test_apply_profile_updates_marks_profile_as_configured() -> None:
    brain = AssistantBrain()
    state = SessionState()

    updated = brain.apply_profile_updates("Hi, call me Taylor and I like coding, music", state)

    assert updated is True
    assert state.user_name == "Taylor"
    assert state.interests == ["coding", "music"]
    assert state.profile.has_met_user is True
    assert state.onboarding_complete is True
