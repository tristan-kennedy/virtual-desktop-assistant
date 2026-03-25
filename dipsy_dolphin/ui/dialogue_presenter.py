from __future__ import annotations

from dataclasses import dataclass

from .presentation_models import ResolvedTurnPresentation


MAX_DIALOGUE_QUEUE = 2


@dataclass(frozen=True)
class DialogueItem:
    text: str
    cue: ResolvedTurnPresentation
    reveal_steps: tuple[str, ...]
    hold_ms: int
    utterance_id: str = ""


class DialoguePresenter:
    def __init__(self, max_queue: int = MAX_DIALOGUE_QUEUE) -> None:
        self.max_queue = max_queue
        self.active_item: DialogueItem | None = None
        self.queue: list[DialogueItem] = []
        self.reveal_index = 0

    def clear(self) -> None:
        self.active_item = None
        self.queue.clear()
        self.reveal_index = 0

    def enqueue(
        self,
        text: str,
        cue: ResolvedTurnPresentation,
        *,
        hold_override_ms: int | None = None,
        utterance_id: str = "",
    ) -> str:
        item = build_dialogue_item(
            text,
            cue,
            hold_override_ms=hold_override_ms,
            utterance_id=utterance_id,
        )
        if self.active_item is None:
            self._start(item)
            return "start"

        active_item = self.active_item
        active_priority = active_item.cue.delivery.interrupt_priority
        incoming_priority = item.cue.delivery.interrupt_priority
        active_replaceable = active_item.cue.delivery.replaceable

        if active_replaceable and incoming_priority >= active_priority:
            self._start(item)
            return "replace"

        if item.cue.delivery.queue_policy == "replace" and incoming_priority >= active_priority:
            self._start(item)
            return "replace"

        if item.cue.delivery.queue_policy == "queue" and len(self.queue) < self.max_queue:
            self.queue.append(item)
            return "queue"

        return "drop"

    def active_text(self) -> str:
        if self.active_item is None:
            return ""
        return self.active_item.reveal_steps[self.reveal_index]

    def active_hold_ms(self) -> int:
        if self.active_item is None:
            return 0
        return self.active_item.hold_ms

    def active_chunk_pause_ms(self) -> int:
        if self.active_item is None:
            return 0
        return self.active_item.cue.delivery.chunk_pause_ms

    def active_remaining_duration_ms(self) -> int:
        if self.active_item is None:
            return 0
        remaining_reveals = len(self.active_item.reveal_steps) - self.reveal_index - 1
        reveal_ms = max(0, remaining_reveals) * self.active_chunk_pause_ms()
        return reveal_ms + self.active_hold_ms()

    def has_more_reveal(self) -> bool:
        if self.active_item is None:
            return False
        return self.reveal_index < len(self.active_item.reveal_steps) - 1

    def advance_reveal(self) -> bool:
        if not self.has_more_reveal():
            return False
        self.reveal_index += 1
        return True

    def finish_active(self) -> bool:
        if not self.queue:
            self.active_item = None
            self.reveal_index = 0
            return False
        next_item = self.queue.pop(0)
        self._start(next_item)
        return True

    def _start(self, item: DialogueItem) -> None:
        self.active_item = item
        self.reveal_index = 0


def build_dialogue_item(
    text: str,
    cue: ResolvedTurnPresentation,
    *,
    hold_override_ms: int | None = None,
    utterance_id: str = "",
) -> DialogueItem:
    cleaned_text = " ".join(text.split())
    reveal_steps = build_reveal_steps(cleaned_text, cue)
    hold_ms = (
        hold_override_ms if hold_override_ms is not None else _hold_duration_ms(cleaned_text, cue)
    )
    return DialogueItem(
        text=cleaned_text,
        cue=cue,
        reveal_steps=reveal_steps,
        hold_ms=hold_ms,
        utterance_id=utterance_id,
    )


def build_reveal_steps(text: str, cue: ResolvedTurnPresentation) -> tuple[str, ...]:
    if not text:
        return ("",)

    delivery = cue.delivery
    if delivery.reveal_mode == "instant" or len(text) <= delivery.chunk_chars:
        return (text,)

    words = text.split()
    chunks: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if current and len(candidate) > delivery.chunk_chars:
            chunks.append(current)
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current)

    reveal_steps: list[str] = []
    visible = ""
    for chunk in chunks:
        visible = chunk if not visible else f"{visible} {chunk}"
        reveal_steps.append(visible)
    return tuple(reveal_steps)


def _hold_duration_ms(text: str, cue: ResolvedTurnPresentation) -> int:
    delivery = cue.delivery
    words = max(1, len(text.split()))
    base = delivery.hold_ms + min(5000, words * 160)
    if cue.dialogue_category in {"status", "onboarding"}:
        base += 600
    return max(1400, min(12000, base))
