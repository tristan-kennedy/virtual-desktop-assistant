from dipsy_dolphin.core.controller import AssistantController
from dipsy_dolphin.core.models import SessionState


class StubProvider:
    resolved_bundle = None

    class Status:
        reason = ""

    status = Status()

    def is_available(self) -> bool:
        return True

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        assert "Dipsy Dolphin" in system_prompt
        assert "event" in user_prompt
        return {
            "say": "I am fully awake and ready to loiter theatrically.",
            "animation": "excited",
            "speech_style": "normal",
            "action": {"action_id": "roam_somewhere", "args": {}},
            "cooldown_ms": 14000,
            "topic": "startup",
        }


class UnavailableProvider:
    resolved_bundle = None

    class Status:
        reason = "No bundled local model was found"

    status = Status()

    def is_available(self) -> bool:
        return False

    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        raise RuntimeError("should not be called")


class SilentActionProvider(StubProvider):
    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        return {
            "say": "",
            "animation": "idle",
            "speech_style": "normal",
            "action": {"action_id": "idle", "args": {}},
            "cooldown_ms": 12000,
            "topic": "action",
        }


class LongReplyProvider(StubProvider):
    def generate(self, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        return {
            "say": "A" * 500,
            "animation": "talk",
            "speech_style": "normal",
            "action": None,
            "cooldown_ms": 12000,
            "topic": "chat",
        }


def test_controller_uses_llm_turn_when_provider_is_available() -> None:
    controller = AssistantController(provider=StubProvider())
    state = SessionState()

    result = controller.startup_turn(state)

    assert result.turn.say == "I am fully awake and ready to loiter theatrically."
    assert result.turn.animation == "excited"
    assert result.turn.action is not None
    assert result.turn.action.action_id == "roam_somewhere"
    assert state.last_assistant_line == ""
    assert result.session_state is not None
    assert result.session_state.last_assistant_line == result.turn.say


def test_do_something_turn_forces_visible_response() -> None:
    controller = AssistantController(provider=SilentActionProvider())
    state = SessionState()

    result = controller.do_something_turn(state)

    assert result.turn.say == "Stand back. I am preparing a tasteful burst of desktop theater."
    assert result.turn.animation == "excited"


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
    controller = AssistantController(provider=LongReplyProvider())
    state = SessionState()

    result = controller.handle_user_message("Tell me something longer", state)

    assert len(result.turn.say) == 500
