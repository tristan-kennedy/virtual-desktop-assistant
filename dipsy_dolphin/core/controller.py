from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any, Protocol

from .autonomy import AutonomyPlan
from ..llm.config import discover_model_bundle
from ..llm.local_provider import LocalLlamaProvider
from ..llm.prompt_builder import build_system_prompt, build_user_prompt
from ..llm.response_parser import parse_assistant_turn
from .brain import AssistantBrain
from .controller_models import ActionRequest, AssistantTurn, ControllerResult
from .models import SessionState


MAX_SPOKEN_CHARACTERS = 1200


class ControllerProvider(Protocol):
    resolved_bundle: Any | None
    status: Any

    def is_available(self) -> bool: ...

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]: ...


class AssistantController:
    def __init__(
        self,
        brain: AssistantBrain | None = None,
        provider: ControllerProvider | None = None,
    ) -> None:
        self.brain = brain or AssistantBrain()
        self.provider = provider or LocalLlamaProvider(discover_model_bundle())
        if not self.provider.is_available():
            raise RuntimeError(self._required_llm_message())

    def startup_turn(self, state: SessionState) -> ControllerResult:
        return self._build_result(
            "startup",
            state,
            defaults=AssistantTurn(
                animation="surprised" if not state.onboarding_complete else "talk",
                speech_style="onboarding" if not state.onboarding_complete else "status",
                cooldown_ms=9000,
                topic="startup",
                source="llm",
            ),
        )

    def onboarding_name_prompt(self, state: SessionState) -> ControllerResult:
        return self._build_result(
            "onboarding_name",
            state,
            defaults=AssistantTurn(
                animation="surprised",
                speech_style="onboarding",
                cooldown_ms=5000,
                topic="onboarding",
                source="llm",
            ),
        )

    def onboarding_interest_prompt(self, state: SessionState) -> ControllerResult:
        return self._build_result(
            "onboarding_interests",
            state,
            defaults=AssistantTurn(
                animation="surprised",
                speech_style="onboarding",
                cooldown_ms=6500,
                topic="onboarding",
                source="llm",
            ),
        )

    def finish_onboarding(self, state: SessionState) -> ControllerResult:
        return self._build_result(
            "onboarding_finish",
            state,
            defaults=AssistantTurn(
                animation="excited",
                speech_style="normal",
                cooldown_ms=9000,
                topic="onboarding",
                source="llm",
            ),
        )

    def handle_user_message(self, text: str, state: SessionState) -> ControllerResult:
        clean = text.strip()
        if not clean:
            raise ValueError("User message cannot be empty")

        return self._build_result(
            "chat",
            state,
            user_text=clean,
            defaults=AssistantTurn(
                animation="talk",
                speech_style="normal",
                cooldown_ms=15000,
                topic=state.last_topic or "chat",
                source="llm",
            ),
        )

    def parse_interests(self, raw_text: str) -> list[str]:
        return self.brain.parse_interests(raw_text)

    def shutdown(self) -> None:
        shutdown = getattr(self.provider, "shutdown", None)
        if callable(shutdown):
            shutdown()

    def autonomous_turn(
        self,
        state: SessionState,
        plan: AutonomyPlan | None = None,
        *,
        seconds_since_user_interaction: int | None = None,
    ) -> ControllerResult:
        active_plan = plan or AutonomyPlan(
            mode="idle",
            allowed_behaviors=("idle", "emote"),
            guidance="Prefer a quiet beat.",
            minimum_cooldown_ms=12000,
            base_weight=1,
        )
        return self._build_result(
            "autonomous",
            state,
            defaults=AssistantTurn(
                animation="idle",
                speech_style="normal",
                cooldown_ms=12000,
                behavior=active_plan.mode,
                topic=state.last_topic or "idle",
                source="llm",
            ),
            event_context={
                "autonomy_plan": active_plan.prompt_payload(
                    seconds_since_user_interaction=seconds_since_user_interaction
                )
            },
            minimum_cooldown_ms=active_plan.minimum_cooldown_ms,
        )

    def do_something_turn(self, state: SessionState) -> ControllerResult:
        return self._build_result(
            "do_something",
            state,
            defaults=AssistantTurn(
                animation="excited",
                speech_style="normal",
                cooldown_ms=12000,
                behavior="action",
                topic="action",
                source="llm",
            ),
        )

    def joke_turn(self, state: SessionState) -> ControllerResult:
        return self._build_result(
            "joke",
            state,
            defaults=AssistantTurn(
                animation="laugh",
                speech_style="joke",
                cooldown_ms=10000,
                behavior="joke",
                topic="joke",
                source="llm",
            ),
        )

    def status_turn(self, state: SessionState) -> ControllerResult:
        return self._build_result(
            "status",
            state,
            defaults=AssistantTurn(
                animation="talk",
                speech_style="status",
                cooldown_ms=9000,
                behavior="status",
                topic="status",
                source="llm",
            ),
        )

    def reset_turn(self, state: SessionState) -> ControllerResult:
        return self._build_result(
            "reset",
            state,
            defaults=AssistantTurn(
                animation="surprised",
                speech_style="alert",
                cooldown_ms=5000,
                behavior="reset",
                topic="reset",
                source="llm",
            ),
        )

    def _build_result(
        self,
        event: str,
        state: SessionState,
        *,
        defaults: AssistantTurn,
        user_text: str = "",
        event_context: dict[str, object] | None = None,
        minimum_cooldown_ms: int | None = None,
    ) -> ControllerResult:
        working_state = copy.deepcopy(state)
        if event == "chat" and user_text:
            working_state.remember_user_turn(user_text)
            self.brain.apply_profile_updates(user_text, working_state)
        elif event == "reset":
            self.brain.reset_state(working_state)
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(event, working_state, user_text, context=event_context)

        try:
            parsed_turn = self._request_turn(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as exc:
            raise RuntimeError(f"Local brain failed during '{event}': {exc}") from exc

        turn = self._apply_defaults(
            parsed_turn,
            defaults,
            event=event,
            required_speech=self._speech_required(event),
            required_visible=self._visible_response_required(event),
            minimum_cooldown_ms=minimum_cooldown_ms,
        )
        if self._speech_required(event) and not turn.say:
            raise RuntimeError(f"Local brain returned no speech for required event '{event}'")

        self._remember_turn(turn, working_state)
        if event == "autonomous":
            working_state.autonomous_beats += 1
            working_state.remember_autonomous_behavior(self._autonomous_behavior_for_turn(turn))
            if turn.say:
                working_state.autonomous_chats += 1
        working_state.last_topic = turn.topic or working_state.last_topic
        working_state.autonomy_cooldown_ms = turn.cooldown_ms
        return ControllerResult(turn=turn, session_state=working_state)

    def _request_turn(self, *, system_prompt: str, user_prompt: str) -> AssistantTurn:
        payload = self.provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        return parse_assistant_turn(payload)

    def _apply_defaults(
        self,
        parsed_turn: AssistantTurn,
        defaults: AssistantTurn,
        *,
        event: str,
        required_speech: bool,
        required_visible: bool,
        minimum_cooldown_ms: int | None,
    ) -> AssistantTurn:
        turn = replace(
            parsed_turn,
            say=parsed_turn.say.strip(),
            animation=parsed_turn.animation or defaults.animation,
            speech_style=parsed_turn.speech_style or defaults.speech_style,
            cooldown_ms=max(
                parsed_turn.cooldown_ms or defaults.cooldown_ms, minimum_cooldown_ms or 0
            ),
            behavior=parsed_turn.behavior or defaults.behavior,
            topic=parsed_turn.topic or defaults.topic,
            source="llm",
        )

        if event == "autonomous" and turn.behavior == "roam" and turn.action is None:
            turn = replace(turn, action=ActionRequest(action_id="roam_somewhere", args={}))

        if required_speech and not turn.say:
            return replace(
                turn, say="I have a thought, but it slipped behind the curtain. Try me again."
            )

        if required_visible and not turn.say and self._is_non_visible_turn(turn):
            return replace(
                turn,
                say="Stand back. I am preparing a tasteful burst of desktop theater.",
                animation="excited",
                behavior=turn.behavior or defaults.behavior or "action",
                speech_style="normal",
                topic=turn.topic or defaults.topic or "action",
            )

        if event == "autonomous" and self._is_silent_autonomous_emote(turn):
            return turn

        if not required_speech and not turn.say and turn.action is None:
            return replace(
                turn,
                animation="idle",
                action=ActionRequest(action_id="idle", args={}),
                behavior=turn.behavior or defaults.behavior or "idle",
            )

        if turn.say and len(turn.say) > MAX_SPOKEN_CHARACTERS:
            shortened = turn.say[: MAX_SPOKEN_CHARACTERS - 3].rstrip(" ,.;:!") + "..."
            return replace(turn, say=shortened)

        return turn

    def _remember_turn(self, turn: AssistantTurn, state: SessionState) -> None:
        if turn.say:
            state.remember_assistant_turn(turn.say)

    def _speech_required(self, event: str) -> bool:
        return event not in {"autonomous", "do_something"}

    def _visible_response_required(self, event: str) -> bool:
        return event in {
            "startup",
            "onboarding_name",
            "onboarding_interests",
            "onboarding_finish",
            "chat",
            "joke",
            "status",
            "reset",
            "do_something",
        }

    def _is_non_visible_turn(self, turn: AssistantTurn) -> bool:
        if turn.action is not None and turn.action.action_id != "idle":
            return False
        return turn.animation == "idle"

    def _is_silent_autonomous_emote(self, turn: AssistantTurn) -> bool:
        return (
            turn.action is None
            and not turn.say
            and turn.animation
            in {
                "think",
                "laugh",
                "surprised",
                "sad",
                "excited",
            }
        )

    def _autonomous_behavior_for_turn(self, turn: AssistantTurn) -> str:
        if turn.behavior:
            return turn.behavior
        if turn.action is not None:
            if turn.action.action_id == "roam_somewhere":
                return "roam"
            return "idle"
        if turn.say:
            return "quip"
        if turn.animation == "idle":
            return "idle"
        return "emote"

    def _required_llm_message(self) -> str:
        return (
            "Dipsy Dolphin requires a bundled local LLM to start.\n\n"
            "Local development setup:\n"
            "1. Run `uv sync --group local-llm`\n"
            "2. Download the bundled model with `uv run python -m scripts.windows_build model-bundle`\n"
            "3. Start the app with `uv run dipsy-dolphin`\n\n"
            f"Current issue: {getattr(self.provider.status, 'reason', '') or 'local brain unavailable'}"
        )
