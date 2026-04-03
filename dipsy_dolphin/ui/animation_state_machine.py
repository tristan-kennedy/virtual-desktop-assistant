from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class AnimationStateConfig:
    priority: int
    min_hold_ms: int
    cooldown_ms: int = 0


@dataclass
class ActiveAnimationState:
    name: str
    started_ms: int
    expires_ms: Optional[int] = None


class AnimationStateMachine:
    """Owns transient animation_state requests and motion/base-state arbitration.

    This machine does not know about higher-level scene semantics.
    It only resolves which animation state should currently be active.
    """

    def __init__(self) -> None:
        self._configs: Dict[str, AnimationStateConfig] = {
            "idle": AnimationStateConfig(priority=0, min_hold_ms=0),
            "walk": AnimationStateConfig(priority=0, min_hold_ms=0),
            "loading": AnimationStateConfig(priority=2, min_hold_ms=600),
            "think": AnimationStateConfig(priority=2, min_hold_ms=350),
            "talk": AnimationStateConfig(priority=3, min_hold_ms=450),
            "laugh": AnimationStateConfig(priority=4, min_hold_ms=1100, cooldown_ms=2200),
            "surprised": AnimationStateConfig(priority=4, min_hold_ms=900, cooldown_ms=1800),
            "sad": AnimationStateConfig(priority=3, min_hold_ms=1300, cooldown_ms=1500),
            "excited": AnimationStateConfig(priority=4, min_hold_ms=1200, cooldown_ms=2000),
        }
        self._base_state = "idle"
        self._active_state: Optional[ActiveAnimationState] = None
        self._cooldowns: Dict[str, int] = {}
        self.facing = "right"

    def set_base_state(self, state: str, now_ms: int, delta_x: float = 0) -> None:
        self._require_known_state(state)
        self._expire_if_needed(now_ms)
        self._base_state = state
        self._set_facing_from_delta(delta_x)

    def request_state(
        self,
        state: str,
        now_ms: int,
        *,
        duration_ms: Optional[int] = None,
        delta_x: float = 0,
        force: bool = False,
    ) -> bool:
        self._require_known_state(state)
        self._expire_if_needed(now_ms)
        self._set_facing_from_delta(delta_x)

        if self._active_state and self._active_state.name == state:
            if duration_ms is not None:
                requested_expiry = now_ms + duration_ms
                if self._active_state.expires_ms is None:
                    self._active_state.expires_ms = requested_expiry
                else:
                    self._active_state.expires_ms = max(
                        self._active_state.expires_ms, requested_expiry
                    )
            return True

        if not force and self._is_on_cooldown(state, now_ms):
            return False

        current_state = self.current_state(now_ms)
        current_config = self._configs[current_state]
        target_config = self._configs[state]

        if (
            not force
            and self._active_state is not None
            and now_ms < self._active_state.started_ms + current_config.min_hold_ms
            and target_config.priority <= current_config.priority
        ):
            return False

        self._active_state = ActiveAnimationState(
            name=state,
            started_ms=now_ms,
            expires_ms=None if duration_ms is None else now_ms + duration_ms,
        )
        return True

    def clear_active_state(self, now_ms: int, *, force: bool = False) -> bool:
        self._expire_if_needed(now_ms)
        if self._active_state is None:
            return False

        config = self._configs[self._active_state.name]
        if not force and now_ms < self._active_state.started_ms + config.min_hold_ms:
            return False

        self._finish_active_state(now_ms)
        return True

    def current_state(self, now_ms: int) -> str:
        self._expire_if_needed(now_ms)
        if self._active_state is not None:
            return self._active_state.name
        return self._base_state

    def _expire_if_needed(self, now_ms: int) -> None:
        if self._active_state is None or self._active_state.expires_ms is None:
            return

        if now_ms >= self._active_state.expires_ms:
            self._finish_active_state(now_ms)

    def _finish_active_state(self, now_ms: int) -> None:
        if self._active_state is None:
            return

        config = self._configs[self._active_state.name]
        if config.cooldown_ms > 0:
            self._cooldowns[self._active_state.name] = now_ms + config.cooldown_ms
        self._active_state = None

    def _is_on_cooldown(self, state: str, now_ms: int) -> bool:
        return now_ms < self._cooldowns.get(state, 0)

    def _set_facing_from_delta(self, delta_x: float) -> None:
        if delta_x > 1:
            self.facing = "right"
        elif delta_x < -1:
            self.facing = "left"

    def _require_known_state(self, state: str) -> None:
        if state not in self._configs:
            raise ValueError(f"Unknown animation state: {state}")
