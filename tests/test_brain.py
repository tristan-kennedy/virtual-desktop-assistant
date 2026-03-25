from dipsy_dolphin.core.brain import AssistantBrain
from dipsy_dolphin.core.memory import MemoryEntry
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
    assert state.memory.identity.has_met_user is True
    assert state.onboarding_complete is True


def test_reset_state_clears_autonomy_scheduler_memory() -> None:
    brain = AssistantBrain()
    state = SessionState()
    state.memory.long_term_facts.append(
        MemoryEntry(
            memory_id="fact-1", value="lives in Seattle", created_at_utc="2026-03-24T00:00:00Z"
        )
    )
    state.last_autonomous_behavior = "joke"
    state.recent_autonomous_behaviors = ["quip", "joke"]
    state.last_autonomous_at_ms = 22_000
    state.autonomous_behavior_times_ms = {"joke": 22_000}
    state.autonomy_cooldown_ms = 18_000

    brain.reset_state(state)

    assert state.last_autonomous_behavior == ""
    assert state.recent_autonomous_behaviors == []
    assert state.last_autonomous_at_ms == 0
    assert state.autonomous_behavior_times_ms == {}
    assert state.autonomy_cooldown_ms == 0
    assert state.memory.has_entries() is False
