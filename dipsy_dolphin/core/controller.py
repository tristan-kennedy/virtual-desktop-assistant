from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any, Protocol

from ..actions.executor import ActionExecutor, ActionExecutorProtocol
from ..actions.models import ExecutionResult
from ..llm.config import discover_model_bundle
from ..llm.local_provider import LocalLlamaProvider
from ..llm.prompt_builder import build_system_prompt, build_user_prompt
from ..llm.response_parser import parse_assistant_turn
from .brain import AssistantBrain
from .controller_models import (
    AssistantTurn,
    ControllerLoopStep,
    ControllerResult,
)
from .emotion import EmotionState
from .memory import apply_memory_updates
from .models import SessionState


MAX_SPOKEN_CHARACTERS = 1200
ACTION_RESULT_EVENT = "action_result"
INACTIVE_TICK_EVENT = "inactive_tick"
MAX_ACTION_STEPS = 2
MAX_MODEL_PASSES = 3


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
        action_executor: ActionExecutorProtocol | None = None,
    ) -> None:
        self.brain = brain or AssistantBrain()
        self.provider = provider or LocalLlamaProvider(discover_model_bundle())
        self.action_executor = action_executor or ActionExecutor()
        if not self.provider.is_available():
            raise RuntimeError(self._required_llm_message())

    def startup_turn(self, state: SessionState) -> ControllerResult:
        return self._build_result(
            "startup",
            state,
            defaults=AssistantTurn(
                animation="surprised" if not state.onboarding_complete else "talk",
                dialogue_category="onboarding" if not state.onboarding_complete else "status",
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
                dialogue_category="onboarding",
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
                dialogue_category="onboarding",
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
                dialogue_category="onboarding",
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
                dialogue_category="normal",
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

    def inactivity_turn(
        self,
        state: SessionState,
        *,
        seconds_since_user_interaction: int | None = None,
        cooldown_remaining_ms: int | None = None,
    ) -> ControllerResult:
        return self._build_result(
            INACTIVE_TICK_EVENT,
            state,
            defaults=AssistantTurn(
                animation="idle",
                dialogue_category="thought",
                cooldown_ms=12000,
                behavior="idle",
                topic=state.last_topic or "inactivity",
                source="llm",
            ),
            event_context={
                "seconds_since_user_interaction": seconds_since_user_interaction,
                "cooldown_remaining_ms": cooldown_remaining_ms,
            },
        )

    def autonomous_turn(
        self,
        state: SessionState,
        *,
        seconds_since_user_interaction: int | None = None,
        cooldown_remaining_ms: int | None = None,
    ) -> ControllerResult:
        return self.inactivity_turn(
            state,
            seconds_since_user_interaction=seconds_since_user_interaction,
            cooldown_remaining_ms=cooldown_remaining_ms,
        )

    def do_something_turn(self, state: SessionState) -> ControllerResult:
        return self._build_result(
            "do_something",
            state,
            defaults=AssistantTurn(
                animation="excited",
                dialogue_category="normal",
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
                dialogue_category="joke",
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
                dialogue_category="status",
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
                dialogue_category="alert",
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
        required_speech = self._speech_required(event)
        required_visible = self._visible_response_required(event)
        if event == "chat" and user_text:
            working_state.remember_user_turn(user_text)
            self.brain.apply_profile_updates(user_text, working_state)
        elif event == "reset":
            self.brain.reset_state(working_state)
        defaults = replace(defaults, emotion=working_state.emotion)

        loop_steps: list[ControllerLoopStep] = []
        last_execution_result: ExecutionResult | None = None
        loop_stop_reason = "no_action"
        request_event = event
        request_context = event_context
        executed_action_steps = 0
        final_turn: AssistantTurn | None = None

        for step_index in range(1, MAX_MODEL_PASSES + 1):
            is_initial_pass = step_index == 1
            try:
                turn = self._request_and_apply_turn(
                    event=request_event,
                    state=working_state,
                    user_text=user_text,
                    context=request_context,
                    defaults=defaults,
                    required_speech=False if is_initial_pass else required_speech,
                    required_visible=False if is_initial_pass else required_visible,
                    minimum_cooldown_ms=minimum_cooldown_ms,
                    memory_updates_enabled=event == "chat",
                )
            except Exception:
                if executed_action_steps <= 0:
                    raise
                final_turn = self._followup_error_turn(
                    defaults=defaults,
                    execution_result=last_execution_result,
                )
                loop_stop_reason = "followup_error"
                break

            if turn.action is not None and executed_action_steps >= MAX_ACTION_STEPS:
                loop_steps.append(
                    ControllerLoopStep(
                        step_index=step_index,
                        event=request_event,
                        turn=turn,
                        execution_result=None,
                    )
                )
                final_turn = self._loop_limit_turn(defaults=defaults)
                loop_stop_reason = "step_limit"
                break

            execution_result = self._execute_action(turn)
            if execution_result is not None:
                last_execution_result = execution_result
                executed_action_steps += 1

            loop_steps.append(
                ControllerLoopStep(
                    step_index=step_index,
                    event=request_event,
                    turn=turn,
                    execution_result=execution_result,
                )
            )

            if execution_result is None:
                final_turn = self._finalize_visible_turn(
                    turn,
                    defaults=defaults,
                    required_speech=required_speech,
                    required_visible=required_visible,
                )
                loop_stop_reason = (
                    "completed_after_action" if executed_action_steps > 0 else "no_action"
                )
                break

            if step_index >= MAX_MODEL_PASSES:
                final_turn = self._loop_limit_turn(defaults=defaults)
                loop_stop_reason = "step_limit"
                break

            request_event = ACTION_RESULT_EVENT
            request_context = self._action_result_context(
                original_event=event,
                original_user_text=user_text,
                loop_steps=loop_steps,
            )

        if final_turn is None:
            final_turn = self._loop_limit_turn(defaults=defaults)
            loop_stop_reason = "step_limit"

        self._remember_turn(final_turn, working_state)
        if event == INACTIVE_TICK_EVENT:
            working_state.autonomous_beats += 1
            working_state.remember_autonomous_behavior(
                self._autonomous_behavior_for_turn(final_turn)
            )
            if final_turn.say:
                working_state.autonomous_chats += 1
        if event == "chat" and final_turn.memory_updates:
            working_state.memory = apply_memory_updates(working_state.memory, final_turn.memory_updates)
        if final_turn.emotion is not None:
            working_state.emotion = final_turn.emotion
        working_state.last_topic = final_turn.topic or working_state.last_topic
        working_state.autonomy_cooldown_ms = final_turn.cooldown_ms
        return ControllerResult(
            turn=final_turn,
            session_state=working_state,
            execution_result=last_execution_result,
            loop_steps=tuple(loop_steps),
            loop_stop_reason=loop_stop_reason,
        )

    def _request_and_apply_turn(
        self,
        *,
        event: str,
        state: SessionState,
        user_text: str,
        context: dict[str, object] | None,
        defaults: AssistantTurn,
        required_speech: bool,
        required_visible: bool,
        minimum_cooldown_ms: int | None,
        memory_updates_enabled: bool,
    ) -> AssistantTurn:
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(event, state, user_text, context=context)

        try:
            parsed_turn = self._request_turn(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                fallback_emotion=state.emotion,
            )
        except Exception as exc:
            raise RuntimeError(f"Local brain failed during '{event}': {exc}") from exc

        return self._apply_defaults(
            parsed_turn,
            defaults,
            event=event,
            required_speech=required_speech,
            required_visible=required_visible,
            minimum_cooldown_ms=minimum_cooldown_ms,
            memory_updates_enabled=memory_updates_enabled,
        )

    def _request_turn(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        fallback_emotion: EmotionState,
    ) -> AssistantTurn:
        payload = self.provider.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        return parse_assistant_turn(payload, fallback_emotion=fallback_emotion)

    def _apply_defaults(
        self,
        parsed_turn: AssistantTurn,
        defaults: AssistantTurn,
        *,
        event: str,
        required_speech: bool,
        required_visible: bool,
        minimum_cooldown_ms: int | None,
        memory_updates_enabled: bool,
    ) -> AssistantTurn:
        turn = replace(
            parsed_turn,
            say=parsed_turn.say.strip(),
            animation=parsed_turn.animation or defaults.animation,
            dialogue_category=parsed_turn.dialogue_category or defaults.dialogue_category,
            memory_updates=parsed_turn.memory_updates if memory_updates_enabled else (),
            emotion=parsed_turn.emotion or defaults.emotion,
            cooldown_ms=max(
                parsed_turn.cooldown_ms or defaults.cooldown_ms, minimum_cooldown_ms or 0
            ),
            behavior=parsed_turn.behavior or defaults.behavior,
            topic=parsed_turn.topic or defaults.topic,
            source="llm",
        )

        if turn.say and len(turn.say) > MAX_SPOKEN_CHARACTERS:
            shortened = turn.say[: MAX_SPOKEN_CHARACTERS - 3].rstrip(" ,.;:!") + "..."
            return replace(turn, say=shortened)

        return turn

    def _remember_turn(self, turn: AssistantTurn, state: SessionState) -> None:
        if turn.say:
            state.remember_assistant_turn(turn.say)

    def _finalize_visible_turn(
        self,
        turn: AssistantTurn,
        *,
        defaults: AssistantTurn,
        required_speech: bool,
        required_visible: bool,
    ) -> AssistantTurn:
        final_turn = turn
        if required_speech and not final_turn.say:
            final_turn = replace(
                final_turn,
                say="I have a thought, but it slipped behind the curtain. Try me again.",
            )

        if required_visible and not final_turn.say and self._is_non_visible_turn(final_turn):
            final_turn = replace(
                final_turn,
                say="Stand back. I am preparing a tasteful burst of desktop theater.",
                animation="excited",
                behavior=final_turn.behavior or defaults.behavior or "action",
                dialogue_category="normal",
                topic=final_turn.topic or defaults.topic or "action",
            )
        return final_turn

    def _execute_action(self, turn: AssistantTurn) -> ExecutionResult | None:
        if turn.action is None:
            return None
        return self.action_executor.execute(turn.action)

    def _action_result_context(
        self,
        *,
        original_event: str,
        original_user_text: str,
        loop_steps: list[ControllerLoopStep],
    ) -> dict[str, object]:
        latest_step = loop_steps[-1]
        return {
            "original_event": original_event,
            "original_user_text": original_user_text,
            "step_index": latest_step.step_index,
            "max_steps": MAX_ACTION_STEPS,
            "latest_execution": self._serialize_execution_result(latest_step.execution_result),
            "loop_steps": [self._serialize_loop_step(step) for step in loop_steps],
        }

    def _serialize_execution_result(
        self,
        execution_result: ExecutionResult | None,
    ) -> dict[str, object]:
        if execution_result is None:
            return {}
        return dict(execution_result.observation)

    def _serialize_loop_step(self, step: ControllerLoopStep) -> dict[str, object]:
        observation = (
            step.execution_result.observation if step.execution_result is not None else {}
        )
        return {
            "step_index": step.step_index,
            "event": step.event,
            "say": step.turn.say,
            "action_id": step.turn.action.action_id if step.turn.action is not None else "",
            "topic": step.turn.topic,
            "execution_status": (
                step.execution_result.status if step.execution_result is not None else ""
            ),
            "execution_message": (
                step.execution_result.message if step.execution_result is not None else ""
            ),
            "operation": str(observation.get("operation", "")),
            "target": str(observation.get("target", "")),
            "resolved_app_id": str(observation.get("resolved_app_id", "")),
            "launched": bool(observation.get("launched", False)),
            "focused": bool(observation.get("focused", False)),
            "opened": bool(observation.get("opened", False)),
            "failure_reason": str(observation.get("failure_reason", "")),
            "directive_kind": (
                step.execution_result.directive.kind
                if step.execution_result is not None and step.execution_result.directive is not None
                else ""
            ),
        }

    def _followup_error_turn(
        self,
        *,
        defaults: AssistantTurn,
        execution_result: ExecutionResult | None,
    ) -> AssistantTurn:
        message = (
            execution_result.message
            if execution_result is not None
            and execution_result.status in {"rejected", "failed"}
            and execution_result.message
            else "That act landed, but I lost the follow-up line backstage."
        )
        return replace(
            defaults,
            say=message,
            animation="surprised",
            dialogue_category="alert",
            topic=defaults.topic or "action",
        )

    def _loop_limit_turn(self, *, defaults: AssistantTurn) -> AssistantTurn:
        return replace(
            defaults,
            say="I need a slightly bigger backstage loop before I chain another move.",
            animation="surprised",
            dialogue_category="alert",
            action=None,
            topic=defaults.topic or "action",
        )

    def _speech_required(self, event: str) -> bool:
        return event not in {INACTIVE_TICK_EVENT, "do_something"}

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
            "2. Download the bundled model with "
            "`uv run python -m scripts.windows_build model-bundle`\n"
            "3. Start the app with `uv run dipsy-dolphin`\n\n"
            "Current issue: "
            f"{getattr(self.provider.status, 'reason', '') or 'local brain unavailable'}"
        )
