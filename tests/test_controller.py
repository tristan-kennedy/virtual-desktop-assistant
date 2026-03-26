import json

from dipsy_dolphin.actions.models import ExecutionResult
from dipsy_dolphin.core.controller import AssistantController
from dipsy_dolphin.core.emotion import EmotionState
from dipsy_dolphin.core.models import SessionState


def _emotion_payload(**overrides: int) -> dict[str, int]:
    payload = EmotionState().to_prompt_payload()
    payload.update(overrides)
    return payload


class SequenceProvider:
    resolved_bundle = None

    class Status:
        reason = ""

    status = Status()

    def __init__(self, *payloads: dict[str, object]) -> None:
        self._payloads = list(payloads)
        self.prompts: list[dict[str, object]] = []

    def is_available(self) -> bool:
        return True

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        assert "Dipsy Dolphin" in system_prompt
        self.prompts.append(json.loads(user_prompt))
        if not self._payloads:
            raise AssertionError("Provider was called more times than expected")
        return self._payloads.pop(0)


class UnavailableProvider:
    resolved_bundle = None

    class Status:
        reason = "No bundled local model was found"

    status = Status()

    def is_available(self) -> bool:
        return False

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        raise RuntimeError("should not be called")


class FollowupFailureProvider(SequenceProvider):
    def __init__(self, first_payload: dict[str, object]) -> None:
        super().__init__(first_payload)

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        prompt = json.loads(user_prompt)
        self.prompts.append(prompt)
        if prompt["event"] == "action_result":
            raise RuntimeError("follow-up model call failed")
        if not self._payloads:
            raise AssertionError("Provider was called more times than expected")
        return self._payloads.pop(0)


class RejectedActionExecutor:
    def execute(self, request) -> ExecutionResult:
        return ExecutionResult(
            action_id=request.action_id,
            status="rejected",
            message="That routine is tangled in the curtain cord.",
        )


def test_controller_uses_followup_turn_after_successful_action() -> None:
    provider = SequenceProvider(
        {
            "say": "I am taking a dramatic lap.",
            "animation": "excited",
            "dialogue_category": "normal",
            "action": {"action_id": "roam_somewhere", "args": {}},
            "emotion": _emotion_payload(mood=72, energy=80, excitement=78, confidence=66),
            "cooldown_ms": 14000,
            "topic": "startup",
        },
        {
            "say": "New coordinates acquired.",
            "animation": "talk",
            "dialogue_category": "normal",
            "action": None,
            "emotion": _emotion_payload(mood=74, energy=79, excitement=76, confidence=68),
            "cooldown_ms": 14000,
            "topic": "startup",
        },
    )
    controller = AssistantController(provider=provider)
    state = SessionState()

    result = controller.startup_turn(state)

    assert result.turn.say == "New coordinates acquired."
    assert result.turn.action is None
    assert result.execution_result is not None
    assert result.execution_result.status == "success"
    assert result.execution_result.directive is not None
    assert result.execution_result.directive.kind == "start_walk"
    assert len(result.loop_steps) == 2
    assert result.loop_stop_reason == "completed_after_action"
    assert provider.prompts[0]["event"] == "startup"
    assert provider.prompts[1]["event"] == "action_result"
    assert provider.prompts[1]["context"]["latest_execution"]["directive_kind"] == "start_walk"
    assert result.session_state is not None
    assert result.session_state.last_assistant_line == result.turn.say
    assert result.session_state.emotion == EmotionState(
        mood=74,
        energy=79,
        excitement=76,
        confidence=68,
        boredom=20,
        familiarity=10,
    )


def test_do_something_turn_forces_visible_response_when_model_stays_silent() -> None:
    controller = AssistantController(
        provider=SequenceProvider(
            {
                "say": "",
                "animation": "idle",
                "dialogue_category": "normal",
                "action": None,
                "cooldown_ms": 12000,
                "topic": "action",
            }
        )
    )
    state = SessionState()

    result = controller.do_something_turn(state)

    assert result.turn.say == "Stand back. I am preparing a tasteful burst of desktop theater."
    assert result.turn.animation == "excited"
    assert result.execution_result is None
    assert len(result.loop_steps) == 1
    assert result.loop_stop_reason == "no_action"


def test_controller_requires_local_model() -> None:
    try:
        AssistantController(provider=UnavailableProvider())
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected AssistantController to require a local model")

    assert "requires a bundled local LLM" in message
    assert "uv sync --group local-llm" in message
    assert "model-bundle" in message


def test_controller_does_not_clip_normal_long_reply_lengths() -> None:
    controller = AssistantController(
        provider=SequenceProvider(
            {
                "say": "A" * 500,
                "animation": "talk",
                "dialogue_category": "normal",
                "action": None,
                "cooldown_ms": 12000,
                "topic": "chat",
            }
        )
    )
    state = SessionState()

    result = controller.handle_user_message("Tell me something longer", state)

    assert len(result.turn.say) == 500


def test_chat_turn_applies_only_final_llm_memory_updates_after_action_followup() -> None:
    controller = AssistantController(
        provider=SequenceProvider(
            {
                "say": "Let me glide and think.",
                "dialogue_category": "normal",
                "animation": "excited",
                "action": {"action_id": "roam_somewhere", "args": {}},
                "memory_updates": [
                    {
                        "action": "remember",
                        "section": "preferences",
                        "value": "should not persist",
                    }
                ],
                "cooldown_ms": 12000,
                "topic": "chat",
            },
            {
                "say": "Noted with theatrical seriousness.",
                "dialogue_category": "normal",
                "animation": "talk",
                "action": None,
                "memory_updates": [
                    {
                        "action": "remember",
                        "section": "preferences",
                        "value": "likes shopping",
                    }
                ],
                "cooldown_ms": 12000,
                "topic": "chat",
            },
        )
    )
    state = SessionState()

    result = controller.handle_user_message("I really like to shop", state)

    assert result.session_state is not None
    assert result.session_state.memory.values_for("preferences") == ["likes shopping"]


def test_inactivity_turn_preserves_silent_emote_and_uses_neutral_event() -> None:
    provider = SequenceProvider(
        {
            "say": "",
            "animation": "surprised",
            "dialogue_category": "thought",
            "action": None,
            "cooldown_ms": 12000,
            "behavior": "emote",
            "topic": "idle",
        }
    )
    controller = AssistantController(provider=provider)
    state = SessionState()

    result = controller.inactivity_turn(
        state,
        seconds_since_user_interaction=42,
        cooldown_remaining_ms=0,
    )

    assert result.turn.say == ""
    assert result.turn.animation == "surprised"
    assert result.turn.action is None
    assert result.turn.behavior == "emote"
    assert result.loop_stop_reason == "no_action"
    assert provider.prompts[0]["event"] == "inactive_tick"
    assert provider.prompts[0]["context"]["seconds_since_user_interaction"] == 42
    assert result.session_state is not None
    assert result.session_state.last_autonomous_behavior == "emote"


def test_inactivity_turn_does_not_apply_memory_updates() -> None:
    controller = AssistantController(
        provider=SequenceProvider(
            {
                "say": "",
                "dialogue_category": "thought",
                "animation": "think",
                "memory_updates": [
                    {
                        "action": "remember",
                        "section": "preferences",
                        "value": "likes shopping",
                    }
                ],
                "behavior": "emote",
                "cooldown_ms": 12000,
                "topic": "idle",
            }
        )
    )
    state = SessionState()

    result = controller.inactivity_turn(state)

    assert result.session_state is not None
    assert result.session_state.memory.values_for("preferences") == []


def test_controller_uses_followup_turn_after_rejected_action() -> None:
    controller = AssistantController(
        provider=SequenceProvider(
            {
                "say": "",
                "animation": "surprised",
                "dialogue_category": "normal",
                "action": {"action_id": "roam_somewhere", "args": {}},
                "cooldown_ms": 12000,
                "topic": "action",
            },
            {
                "say": "That routine is tangled in the curtain cord.",
                "animation": "talk",
                "dialogue_category": "alert",
                "action": None,
                "cooldown_ms": 12000,
                "topic": "action",
            },
        ),
        action_executor=RejectedActionExecutor(),
    )
    state = SessionState()

    result = controller.do_something_turn(state)

    assert result.execution_result is not None
    assert result.execution_result.status == "rejected"
    assert result.turn.say == "That routine is tangled in the curtain cord."
    assert len(result.loop_steps) == 2
    assert result.loop_stop_reason == "completed_after_action"


def test_controller_returns_followup_error_turn_when_second_model_pass_fails() -> None:
    controller = AssistantController(
        provider=FollowupFailureProvider(
            {
                "say": "I am heading stage left.",
                "animation": "excited",
                "dialogue_category": "normal",
                "action": {"action_id": "roam_somewhere", "args": {}},
                "cooldown_ms": 12000,
                "topic": "action",
            }
        )
    )
    state = SessionState()

    result = controller.do_something_turn(state)

    assert result.execution_result is not None
    assert result.execution_result.status == "success"
    assert result.turn.say == "That act landed, but I lost the follow-up line backstage."
    assert result.turn.animation == "surprised"
    assert result.loop_stop_reason == "followup_error"


def test_controller_returns_loop_limit_turn_when_followup_requests_too_many_actions() -> None:
    controller = AssistantController(
        provider=SequenceProvider(
            {
                "say": "First move.",
                "animation": "excited",
                "dialogue_category": "normal",
                "action": {"action_id": "roam_somewhere", "args": {}},
                "cooldown_ms": 12000,
                "topic": "action",
            },
            {
                "say": "Second move.",
                "animation": "excited",
                "dialogue_category": "normal",
                "action": {"action_id": "roam_somewhere", "args": {}},
                "cooldown_ms": 12000,
                "topic": "action",
            },
            {
                "say": "Third move.",
                "animation": "excited",
                "dialogue_category": "normal",
                "action": {"action_id": "roam_somewhere", "args": {}},
                "cooldown_ms": 12000,
                "topic": "action",
            },
        )
    )
    state = SessionState()

    result = controller.do_something_turn(state)

    assert result.execution_result is not None
    assert result.execution_result.status == "success"
    assert result.turn.say == "I need a slightly bigger backstage loop before I chain another move."
    assert result.turn.action is None
    assert len(result.loop_steps) == 3
    assert result.loop_steps[2].turn.action is not None
    assert result.loop_steps[2].execution_result is None
    assert result.loop_stop_reason == "step_limit"


def test_controller_supports_quit_action_and_followup_line() -> None:
    controller = AssistantController(
        provider=SequenceProvider(
            {
                "say": "",
                "animation": "talk",
                "dialogue_category": "normal",
                "action": {"action_id": "quit_app", "args": {}},
                "cooldown_ms": 4000,
                "topic": "goodbye",
            },
            {
                "say": "All right, slipping backstage now.",
                "animation": "talk",
                "dialogue_category": "normal",
                "action": None,
                "cooldown_ms": 4000,
                "topic": "goodbye",
            },
        )
    )
    state = SessionState()

    result = controller.handle_user_message("Okay goodbye!", state)

    assert result.execution_result is not None
    assert result.execution_result.directive is not None
    assert result.execution_result.directive.kind == "request_quit"
    assert result.turn.say == "All right, slipping backstage now."
    assert result.loop_stop_reason == "completed_after_action"
