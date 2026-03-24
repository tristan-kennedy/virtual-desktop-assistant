from dipsy_dolphin.ui.animation_state_machine import AnimationStateMachine


def test_timed_speech_state_returns_to_walk_base_state() -> None:
    machine = AnimationStateMachine()

    machine.set_base_state("walk", 0, delta_x=-12)
    assert machine.current_state(0) == "walk"
    assert machine.facing == "left"

    accepted = machine.request_state("talk", 100, duration_ms=600)

    assert accepted is True
    assert machine.current_state(200) == "talk"
    assert machine.current_state(701) == "walk"


def test_higher_priority_state_can_interrupt_think() -> None:
    machine = AnimationStateMachine()

    machine.request_state("think", 0)
    accepted = machine.request_state("talk", 100, duration_ms=500)

    assert accepted is True
    assert machine.current_state(150) == "talk"


def test_reaction_state_respects_cooldown_before_reuse() -> None:
    machine = AnimationStateMachine()

    first = machine.request_state("laugh", 0, duration_ms=900)
    second = machine.request_state("laugh", 1000, duration_ms=900)
    third = machine.request_state("laugh", 3200, duration_ms=900)

    assert first is True
    assert second is False
    assert third is True
