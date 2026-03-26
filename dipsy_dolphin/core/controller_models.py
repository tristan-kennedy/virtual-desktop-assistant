from dataclasses import dataclass, field
from typing import Any

from ..actions.models import ExecutionResult
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
class ControllerLoopStep:
    step_index: int
    event: str
    turn: AssistantTurn
    execution_result: ExecutionResult | None = None


@dataclass(frozen=True)
class ControllerResult:
    turn: AssistantTurn
    session_state: SessionState | None = None
    execution_result: ExecutionResult | None = None
    loop_steps: tuple[ControllerLoopStep, ...] = field(default_factory=tuple)
    loop_stop_reason: str = "single_turn"
