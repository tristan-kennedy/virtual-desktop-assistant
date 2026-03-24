from typing import Protocol


class LLMProvider(Protocol):
    def is_available(self) -> bool: ...

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]: ...
