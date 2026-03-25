from dataclasses import dataclass, field
from typing import Any

from .emotion import EmotionState
from .memory import MemoryUpdate
from .models import SessionState


@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssistantTurn:
    say: str = ""
    animation: str = ""
    dialogue_category: str = "normal"
    action: ActionRequest | None = None
    memory_updates: tuple[MemoryUpdate, ...] = field(default_factory=tuple)
    emotion: EmotionState | None = None
    cooldown_ms: int = 12000
    behavior: str = ""
    topic: str = ""
    source: str = "llm"


@dataclass(frozen=True)
class ControllerResult:
    turn: AssistantTurn
    session_state: SessionState | None = None
