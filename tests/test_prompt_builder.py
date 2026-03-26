import json

from dipsy_dolphin.core.emotion import EmotionState
from dipsy_dolphin.core.memory import AssistantMemory, MemoryEntry
from dipsy_dolphin.core.models import SessionState
from dipsy_dolphin.llm.prompt_builder import build_system_prompt, build_user_prompt


def test_system_prompt_avoids_literal_stock_example_lines() -> None:
    prompt = build_system_prompt()

    assert "Never copy, quote, or lightly remix literal wording" in prompt
    assert "Absolutely. I am a desktop dolphin, not a spreadsheet" not in prompt
    assert (
        "I tried to organize the ocean once. It turned into absolute current events." not in prompt
    )
    assert "Observe this tiny act of desktop drama." not in prompt
    assert "<one short direct reply>" in prompt
    assert "Never return think yourself" in prompt
    assert "Do not default to leading questions about interests" in prompt
    assert "Longer quiet stretches are good" in prompt
    assert "quit_app" in prompt
    assert "Do not use quit_app for casual sign-offs" in prompt
    assert '"emotion"' in prompt
    assert '"dialogue_category"' in prompt
    assert '"memory_updates"' in prompt
    assert "4000-120000" in prompt


def test_user_prompt_includes_emotion_payload_and_summary() -> None:
    state = SessionState(
        emotion=EmotionState(boredom=77, familiarity=42),
        memory=AssistantMemory(
            long_term_facts=[
                MemoryEntry(
                    memory_id="fact-1",
                    value="lives in Seattle",
                    created_at_utc="2026-03-24T00:00:00Z",
                )
            ],
            preferences=[
                MemoryEntry(
                    memory_id="pref-1",
                    value="likes shopping",
                    created_at_utc="2026-03-24T00:00:01Z",
                )
            ],
        ),
    )

    payload = json.loads(build_user_prompt("status", state))

    assert payload["emotion"]["boredom"] == 77
    assert payload["emotion"]["familiarity"] == 42
    assert "boredom high" in payload["emotion_summary"]
    assert payload["identity"]["user_name"] == "friend"
    assert payload["long_term_facts"] == ["lives in Seattle"]
    assert payload["preferences"] == ["likes shopping"]


def test_action_result_prompt_includes_latest_execution_and_loop_trace() -> None:
    state = SessionState()

    payload = json.loads(
        build_user_prompt(
            "action_result",
            state,
            "Tell me a joke",
            context={
                "original_event": "chat",
                "original_user_text": "Tell me a joke",
                "step_index": 1,
                "max_steps": 2,
                "latest_execution": {
                    "action_id": "roam_somewhere",
                    "status": "success",
                    "message": "Move Dipsy to another spot on screen.",
                    "directive_kind": "start_walk",
                    "args": {},
                },
                "loop_steps": [
                    {
                        "step_index": 1,
                        "event": "chat",
                        "say": "I am taking a dramatic lap.",
                        "action_id": "roam_somewhere",
                        "topic": "chat",
                        "execution_status": "success",
                        "execution_message": "Move Dipsy to another spot on screen.",
                        "directive_kind": "start_walk",
                    }
                ],
            },
        )
    )

    assert payload["event"] == "action_result"
    assert payload["user_text"] == "Tell me a joke"
    assert payload["context"]["original_event"] == "chat"
    assert payload["context"]["latest_execution"]["directive_kind"] == "start_walk"
    assert payload["context"]["loop_steps"][0]["action_id"] == "roam_somewhere"
    assert "If one more allowed action is clearly needed" in payload["instructions"]


def test_inactive_tick_prompt_uses_timing_context_without_behavior_hints() -> None:
    state = SessionState()

    payload = json.loads(
        build_user_prompt(
            "inactive_tick",
            state,
            context={
                "seconds_since_user_interaction": 42,
                "cooldown_remaining_ms": 0,
            },
        )
    )

    assert payload["event"] == "inactive_tick"
    assert payload["context"]["seconds_since_user_interaction"] == 42
    assert payload["context"]["cooldown_remaining_ms"] == 0
    assert "Decide whether to stay silent, speak briefly, or use one allowed action" in payload[
        "instructions"
    ]
    assert "avoid repeatedly steering back to the user's interests" in payload["instructions"]
    assert "Longer cooldowns are fine after a bigger beat" in payload["instructions"]
    assert "Preferred mode for this turn" not in payload["instructions"]
    assert "Allowed behaviors for this turn" not in payload["instructions"]
