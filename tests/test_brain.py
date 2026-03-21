from dipsy_dolphin.core.brain import AssistantBrain
from dipsy_dolphin.core.models import SessionState


def test_parse_interests_normalizes_and_limits_entries() -> None:
    brain = AssistantBrain()

    interests = brain.parse_interests(
        "Games, Music, coding, music, movies, books, robots, everything"
    )

    assert interests == ["games", "music", "coding", "movies", "books"]


def test_handle_user_message_updates_name_from_intro_phrase() -> None:
    brain = AssistantBrain()
    state = SessionState()

    reply = brain.handle_user_message("Hi, call me Taylor", state)

    assert state.user_name == "Taylor"
    assert "Taylor" in reply
