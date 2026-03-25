from dipsy_dolphin.core.emotion import EmotionState
from dipsy_dolphin.llm.response_parser import extract_json_object, parse_assistant_turn


def test_parse_assistant_turn_sanitizes_invalid_fields() -> None:
    turn = parse_assistant_turn(
        {
            "say": "A dramatic hello.",
            "animation": "laser-beam",
            "dialogue_category": "mystery",
            "action": {"action_id": "not-real", "args": {"x": 1}},
            "cooldown_ms": 999999,
            "topic": "Greeting",
        }
    )

    assert turn.say == "A dramatic hello."
    assert turn.animation == ""
    assert turn.dialogue_category == "normal"
    assert turn.action is None
    assert turn.cooldown_ms == 30000
    assert turn.topic == "greeting"


def test_extract_json_object_handles_wrapped_json() -> None:
    payload = 'Here you go:\n```json\n{"say": "Hello", "animation": "talk"}\n```'

    extracted = extract_json_object(payload)

    assert extracted["say"] == "Hello"
    assert extracted["animation"] == "talk"


def test_parse_assistant_turn_blocks_ui_only_think_animation_but_keeps_behavior() -> None:
    turn = parse_assistant_turn(
        {
            "say": "",
            "animation": "think",
            "dialogue_category": "thought",
            "behavior": "emote",
            "cooldown_ms": 8000,
            "topic": "idle",
        }
    )

    assert turn.behavior == "emote"
    assert turn.animation == ""
    assert turn.dialogue_category == "thought"


def test_parse_assistant_turn_uses_fallback_emotion_values() -> None:
    fallback = EmotionState(
        mood=40, energy=45, excitement=20, confidence=55, boredom=30, familiarity=25
    )

    turn = parse_assistant_turn(
        {
            "say": "",
            "animation": "talk",
            "emotion": {"mood": 90, "energy": 110, "boredom": "bad"},
        },
        fallback_emotion=fallback,
    )

    assert turn.emotion == EmotionState(
        mood=90,
        energy=100,
        excitement=20,
        confidence=55,
        boredom=30,
        familiarity=25,
    )


def test_parse_assistant_turn_sanitizes_memory_updates() -> None:
    turn = parse_assistant_turn(
        {
            "say": "Noted.",
            "memory_updates": [
                {
                    "action": "remember",
                    "section": "preferences",
                    "value": "likes shopping",
                },
                {
                    "action": "delete",
                    "section": "preferences",
                    "value": "bad",
                },
            ],
        }
    )

    assert len(turn.memory_updates) == 1
    assert turn.memory_updates[0].action == "remember"
    assert turn.memory_updates[0].section == "preferences"
    assert turn.memory_updates[0].value == "likes shopping"
