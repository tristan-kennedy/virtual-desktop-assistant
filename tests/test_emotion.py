from dipsy_dolphin.core.emotion import EmotionState, sanitize_emotion_payload, seed_emotion_state


def test_seed_emotion_state_raises_familiarity_for_known_user() -> None:
    seeded = seed_emotion_state(
        has_met_user=True,
        user_name="Taylor",
        interests_count=2,
        base=EmotionState(familiarity=12),
    )

    assert seeded.familiarity >= 40


def test_sanitize_emotion_payload_clamps_values() -> None:
    emotion = sanitize_emotion_payload(
        {
            "mood": 105,
            "energy": -10,
            "excitement": 44,
            "confidence": 52,
            "boredom": 88,
            "familiarity": 91,
        }
    )

    assert emotion == EmotionState(
        mood=100,
        energy=0,
        excitement=44,
        confidence=52,
        boredom=88,
        familiarity=91,
    )


def test_emotion_summary_uses_human_readable_bands() -> None:
    summary = EmotionState(mood=20, energy=50, excitement=90).summary()

    assert "mood low" in summary
    assert "energy medium" in summary
    assert "excitement high" in summary
