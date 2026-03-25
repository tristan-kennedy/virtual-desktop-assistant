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
    assert '"emotion"' in prompt
    assert '"dialogue_category"' in prompt
    assert '"memory_updates"' in prompt


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
