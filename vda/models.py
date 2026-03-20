from dataclasses import dataclass, field
from typing import List, Set


@dataclass(frozen=True)
class PermissionSpec:
    id: str
    title: str
    risk_points: int
    pitches: List[str]


@dataclass
class SessionState:
    user_name: str = "friend"
    granted_permissions: Set[str] = field(default_factory=set)
    denied_permissions: Set[str] = field(default_factory=set)
    conversation_history: List[str] = field(default_factory=list)
    lose_announced: bool = False
