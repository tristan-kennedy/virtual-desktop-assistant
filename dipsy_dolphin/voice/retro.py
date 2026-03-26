from __future__ import annotations

from xml.sax.saxutils import escape

from .models import VoiceOption, VoiceSelection, VoiceSettings, normalize_voice_profile


PREFERRED_RETRO_VOICE_NAMES = (
    "sydney",
    "adult male #2",
    "microsoft sam",
    "microsoft mike",
    "microsoft mary",
    "truvoice",
    "lh michael",
    "lh michelle",
    "bonzi",
)
RETRO_HINT_TOKENS = (
    "desktop",
    "sam",
    "mike",
    "mary",
    "classic",
    "truvoice",
    "lernout",
    "robot",
)


def choose_voice(
    voices: list[VoiceOption],
    *,
    requested_id: str = "",
    profile: str = "retro_classic",
) -> VoiceSelection:
    if not voices:
        return VoiceSelection(
            option=None, used_fallback=False, reason="No installed Windows voices"
        )

    clean_requested_id = requested_id.strip().lower()
    if clean_requested_id:
        for voice in voices:
            if voice.voice_id.strip().lower() == clean_requested_id:
                return VoiceSelection(option=voice, used_fallback=False, reason="Requested voice")

    if normalize_voice_profile(profile) != "retro_classic":
        return VoiceSelection(option=voices[0], used_fallback=False, reason="First available voice")

    ranked = sorted(voices, key=_retro_score, reverse=True)
    selected = ranked[0]
    used_fallback = _retro_score(selected) < 300
    reason = (
        "Preferred retro voice" if not used_fallback else "Closest available retro-leaning voice"
    )
    return VoiceSelection(option=selected, used_fallback=used_fallback, reason=reason)


def build_retro_ssml(text: str, *, category: str, settings: VoiceSettings) -> str:
    bounded = settings.bounded()
    escaped_text = _stylize_text(text)
    rate = _rate_percent(_effective_rate_value(bounded))
    pitch = _pitch_value(bounded.pitch)
    return (
        "<speak version='1.0' xml:lang='en-US' xmlns='http://www.w3.org/2001/10/synthesis'>"
        f"<prosody rate='{rate}' pitch='{pitch}'>"
        f"{escaped_text}"
        "</prosody>"
        "</speak>"
    )


def estimate_retro_speech_duration_ms(text: str, *, category: str, settings: VoiceSettings) -> int:
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return 0

    words = max(1, len(cleaned.split()))
    base_duration_ms = int((words / 170.0) * 60_000)
    rate_multiplier = _rate_multiplier(_effective_rate_value(settings.bounded()))
    adjusted_duration_ms = int(base_duration_ms / rate_multiplier)
    return max(1400, min(15_000, adjusted_duration_ms + 280))


def estimate_retro_talk_pulse_ms(
    *, category: str, settings: VoiceSettings, pulse_kind: str = "word"
) -> int:
    base_duration_ms = 700 if pulse_kind == "started" else 420
    rate_multiplier = _rate_multiplier(_effective_rate_value(settings.bounded()))
    adjusted = int(base_duration_ms / rate_multiplier)
    minimum = 240 if pulse_kind == "started" else 150
    maximum = 900 if pulse_kind == "started" else 520
    return max(minimum, min(maximum, adjusted))


def _retro_score(voice: VoiceOption) -> int:
    name = voice.name.strip().lower()
    description = voice.description.strip().lower()
    gender = voice.gender.strip().lower()
    score = 0
    if name in PREFERRED_RETRO_VOICE_NAMES:
        score += 700
    for preferred_name in PREFERRED_RETRO_VOICE_NAMES:
        if preferred_name in name:
            score += 320
        if preferred_name in description:
            score += 180
    for token in RETRO_HINT_TOKENS:
        if token in name:
            score += 90
        if token in description:
            score += 45
    if gender == "male":
        score += 30
    if voice.culture.lower().startswith("en"):
        score += 20
    return score


def _stylize_text(text: str) -> str:
    cleaned = " ".join(text.split()).strip()
    return escape(cleaned)


def _rate_percent(rate: int) -> str:
    bounded = max(-10, min(10, rate))
    return f"{bounded * 9:+d}%"


def _rate_multiplier(rate: int) -> float:
    bounded = max(-10, min(10, rate))
    return max(0.25, 1.0 + (bounded * 0.09))


def _effective_rate_value(settings: VoiceSettings) -> int:
    return settings.bounded().rate


def _pitch_value(pitch: int) -> str:
    bounded = max(-10, min(10, pitch))
    return f"{bounded:+d}st"

