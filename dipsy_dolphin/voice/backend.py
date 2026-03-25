from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from .models import SpeechEvent, SpeechRequest, VoiceOption


@dataclass(frozen=True)
class VoiceBackendStatus:
    available: bool
    reason: str = ""


class VoiceBackend(Protocol):
    @property
    def status(self) -> VoiceBackendStatus: ...

    def is_available(self) -> bool: ...

    def list_voices(self) -> list[VoiceOption]: ...

    def speak(self, request: SpeechRequest, emit: Callable[[SpeechEvent], None]) -> None: ...

    def stop(self) -> None: ...

    def shutdown(self) -> None: ...
