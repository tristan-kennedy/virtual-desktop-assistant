from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesktopOperationResult:
    operation: str
    target: str = ""
    resolved_app_id: str = ""
    status: str = "failed"
    message: str = ""
    launched: bool = False
    focused: bool = False
    opened: bool = False
    failure_reason: str = ""
