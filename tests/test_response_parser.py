from dipsy_dolphin.llm.response_parser import extract_json_object, parse_assistant_turn


def test_parse_assistant_turn_sanitizes_invalid_fields() -> None:
    turn = parse_assistant_turn(
        {
            "say": "A dramatic hello.",
            "animation": "laser-beam",
            "speech_style": "mystery",
            "action": {"action_id": "not-real", "args": {"x": 1}},
            "cooldown_ms": 999999,
            "topic": "Greeting",
        }
    )

    assert turn.say == "A dramatic hello."
    assert turn.animation == "talk"
    assert turn.speech_style == "normal"
    assert turn.action is None
    assert turn.cooldown_ms == 30000
    assert turn.topic == "greeting"


def test_extract_json_object_handles_wrapped_json() -> None:
    payload = 'Here you go:\n```json\n{"say": "Hello", "animation": "talk"}\n```'

    extracted = extract_json_object(payload)

    assert extracted["say"] == "Hello"
    assert extracted["animation"] == "talk"
