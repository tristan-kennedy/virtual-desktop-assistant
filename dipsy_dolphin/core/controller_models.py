from dataclasses import dataclass, field
from typing import Any

from .models import SessionState


@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssistantTurn:
    say: str = ""
    animation: str = "talk"
    speech_style: str = "normal"
    action: ActionRequest | None = None
    cooldown_ms: int = 12000
    topic: str = ""
    source: str = "llm"


@dataclass(frozen=True)
class ControllerResult:
    turn: AssistantTurn
    session_state: SessionState | None = None
