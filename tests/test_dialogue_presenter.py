from dipsy_dolphin.ui.dialogue_presenter import DialoguePresenter, build_dialogue_item
from dipsy_dolphin.ui.presentation_models import (
    BubbleStyle,
    DialogueDelivery,
    ResolvedTurnPresentation,
)


def _cue(
    *,
    category: str = "normal",
    reveal_mode: str = "staged",
    queue_policy: str = "queue",
    replaceable: bool = False,
    priority: int = 3,
    chunk_chars: int = 16,
    hold_ms: int = 2200,
) -> ResolvedTurnPresentation:
    return ResolvedTurnPresentation(
        animation_state="talk",
        bubble_style=BubbleStyle(style_id=category),
        dialogue_category=category,
        delivery=DialogueDelivery(
            reveal_mode=reveal_mode,
            chunk_chars=chunk_chars,
            chunk_pause_ms=120,
            hold_ms=hold_ms,
            interrupt_priority=priority,
            queue_policy=queue_policy,
            replaceable=replaceable,
        ),
    )


def test_build_dialogue_item_creates_staged_cumulative_reveal_steps() -> None:
    item = build_dialogue_item(
        "One two three four five six seven",
        _cue(chunk_chars=12),
    )

    assert item.reveal_steps == (
        "One two",
        "One two three four",
        "One two three four five six",
        "One two three four five six seven",
    )


def test_alert_replaces_replaceable_thought() -> None:
    presenter = DialoguePresenter()

    presenter.enqueue(
        "Thinking...", _cue(category="thought", queue_policy="drop", replaceable=True, priority=1)
    )
    result = presenter.enqueue(
        "Pay attention.",
        _cue(category="alert", reveal_mode="instant", queue_policy="replace", priority=5),
    )

    assert result == "replace"
    assert presenter.active_item is not None
    assert presenter.active_item.text == "Pay attention."


def test_joke_queues_behind_active_normal_line() -> None:
    presenter = DialoguePresenter()

    presenter.enqueue("Hello there friend.", _cue(category="normal"))
    result = presenter.enqueue(
        "A very good joke arrives.", _cue(category="joke", queue_policy="queue")
    )

    assert result == "queue"
    assert len(presenter.queue) == 1
    assert presenter.queue[0].cue.dialogue_category == "joke"


def test_thought_drops_when_busy_with_non_replaceable_line() -> None:
    presenter = DialoguePresenter()

    presenter.enqueue("Important status update.", _cue(category="status", queue_policy="queue"))
    result = presenter.enqueue(
        "Just a thought.",
        _cue(category="thought", queue_policy="drop", replaceable=True, priority=1),
    )

    assert result == "drop"
    assert presenter.active_item is not None
    assert presenter.active_item.cue.dialogue_category == "status"


def test_finish_active_starts_next_queued_item() -> None:
    presenter = DialoguePresenter()

    presenter.enqueue("First line.", _cue(category="normal"))
    presenter.enqueue("Second line.", _cue(category="joke", queue_policy="queue"))

    started_next = presenter.finish_active()

    assert started_next is True
    assert presenter.active_item is not None
    assert presenter.active_item.text == "Second line."
