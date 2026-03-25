from dipsy_dolphin.core.memory import (
    AssistantMemory,
    MemoryUpdate,
    apply_memory_updates,
    clear_identity_memory,
    clear_memory_section,
    migrate_legacy_profile_identity,
)


def test_apply_memory_updates_remembers_and_deduplicates_values() -> None:
    memory = AssistantMemory()

    updated = apply_memory_updates(
        memory,
        [
            MemoryUpdate(action="remember", section="preferences", value="likes shopping"),
            MemoryUpdate(action="remember", section="preferences", value="likes shopping"),
        ],
    )

    assert updated.values_for("preferences") == ["likes shopping"]


def test_apply_memory_updates_forgets_matching_value() -> None:
    memory = apply_memory_updates(
        AssistantMemory(),
        [MemoryUpdate(action="remember", section="long_term_facts", value="lives in Seattle")],
    )

    updated = apply_memory_updates(
        memory,
        [MemoryUpdate(action="forget", section="long_term_facts", value="lives in Seattle")],
    )

    assert updated.values_for("long_term_facts") == []


def test_clear_memory_section_only_clears_requested_section() -> None:
    memory = apply_memory_updates(
        AssistantMemory(),
        [
            MemoryUpdate(action="remember", section="long_term_facts", value="lives in Seattle"),
            MemoryUpdate(action="remember", section="preferences", value="likes shopping"),
        ],
    )

    cleared = clear_memory_section(memory, "preferences")

    assert cleared.values_for("preferences") == []
    assert cleared.values_for("long_term_facts") == ["lives in Seattle"]


def test_clear_identity_memory_resets_onboarding_identity() -> None:
    memory, _migrated = migrate_legacy_profile_identity(
        AssistantMemory(),
        user_name="Taylor",
        interests=["coding", "music"],
        has_met_user=True,
    )

    cleared = clear_identity_memory(memory)

    assert cleared.identity.user_name == "friend"
    assert cleared.identity.interest_values() == []
    assert cleared.identity.has_met_user is False


def test_migrate_legacy_profile_identity_merges_into_memory() -> None:
    memory, migrated = migrate_legacy_profile_identity(
        AssistantMemory(),
        user_name="Taylor",
        interests=["coding", "music"],
        has_met_user=True,
    )

    assert migrated is True
    assert memory.identity.user_name == "Taylor"
    assert memory.identity.interest_values() == ["coding", "music"]
    assert memory.identity.has_met_user is True
