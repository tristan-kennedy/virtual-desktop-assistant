from dipsy_dolphin.voice.models import VoiceOption, VoiceSettings
from dipsy_dolphin.voice.retro import (
    build_retro_ssml,
    choose_voice,
    estimate_retro_speech_duration_ms,
    estimate_retro_talk_pulse_ms,
)


def test_choose_voice_prefers_classic_retro_names() -> None:
    voices = [
        VoiceOption(voice_id="Zira", name="Microsoft Zira Desktop", gender="Female"),
        VoiceOption(voice_id="Sydney", name="Sydney", gender="Male"),
    ]

    selection = choose_voice(voices, profile="retro_classic")

    assert selection.option is not None
    assert selection.option.voice_id == "Sydney"
    assert selection.used_fallback is False


def test_choose_voice_respects_requested_voice_id() -> None:
    voices = [
        VoiceOption(voice_id="Sam", name="Microsoft Sam", gender="Male"),
        VoiceOption(voice_id="Zira", name="Microsoft Zira Desktop", gender="Female"),
    ]

    selection = choose_voice(voices, requested_id="Zira")

    assert selection.option is not None
    assert selection.option.voice_id == "Zira"
    assert selection.used_fallback is False


def test_choose_voice_prefers_brighter_fallback_over_david() -> None:
    voices = [
        VoiceOption(voice_id="David", name="Microsoft David Desktop", gender="Male", age="Adult"),
        VoiceOption(voice_id="Zira", name="Microsoft Zira Desktop", gender="Female", age="Adult"),
    ]

    selection = choose_voice(voices, profile="retro_classic")

    assert selection.option is not None
    assert selection.option.voice_id == "Zira"
    assert selection.used_fallback is True


def test_build_retro_ssml_uses_consistent_prosody_without_extra_breaks() -> None:
    ssml = build_retro_ssml(
        "Hello, friend... Dramatic, isn't it?",
        category="joke",
        settings=VoiceSettings(rate=2, pitch=8),
    )

    assert "<speak" in ssml
    assert "<prosody" in ssml
    assert "pitch='x-high'" in ssml
    assert "range='x-high'" in ssml
    assert "<emphasis" not in ssml
    assert "<break time=" not in ssml


def test_estimated_retro_speech_duration_changes_with_rate() -> None:
    slow_duration = estimate_retro_speech_duration_ms(
        "Hello there, dramatic desktop friend.",
        category="normal",
        settings=VoiceSettings(rate=-3),
    )
    fast_duration = estimate_retro_speech_duration_ms(
        "Hello there, dramatic desktop friend.",
        category="normal",
        settings=VoiceSettings(rate=3),
    )

    assert slow_duration > fast_duration


def test_estimated_talk_pulse_changes_with_rate() -> None:
    slow_pulse = estimate_retro_talk_pulse_ms(
        category="normal",
        settings=VoiceSettings(rate=-3),
        pulse_kind="word",
    )
    fast_pulse = estimate_retro_talk_pulse_ms(
        category="normal",
        settings=VoiceSettings(rate=3),
        pulse_kind="word",
    )

    assert slow_pulse > fast_pulse
