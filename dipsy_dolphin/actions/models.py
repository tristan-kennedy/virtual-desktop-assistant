from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionDirective:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    action_id: str
    status: str
    message: str = ""
    directive: ExecutionDirective | None = None
    observation: dict[str, Any] = field(default_factory=dict)
