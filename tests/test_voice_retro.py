from dipsy_dolphin.voice.models import VoiceOption, VoiceSettings
from dipsy_dolphin.voice.retro import build_retro_ssml, choose_voice


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


def test_build_retro_ssml_adds_prosody_and_breaks() -> None:
    ssml = build_retro_ssml(
        "Hello, friend... Dramatic, isn't it?",
        category="joke",
        settings=VoiceSettings(rate=2, pitch=-1),
    )

    assert "<speak" in ssml
    assert "<prosody" in ssml
    assert "<emphasis" in ssml
    assert "<break time='220ms' />" in ssml
