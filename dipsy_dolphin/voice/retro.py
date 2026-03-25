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
    rate = _rate_percent(bounded.rate + _category_rate_delta(category))
    pitch = _pitch_value(bounded.pitch + _category_pitch_delta(category))
    emphasis = _category_emphasis(category)
    return (
        "<speak version='1.0' xml:lang='en-US' xmlns='http://www.w3.org/2001/10/synthesis'>"
        f"<prosody rate='{rate}' pitch='{pitch}'>"
        f"<emphasis level='{emphasis}'>{escaped_text}</emphasis>"
        "</prosody>"
        "</speak>"
    )


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
    escaped = escape(cleaned)
    escaped = escaped.replace("...", "<break time='220ms' />")
    escaped = escaped.replace("!", "!<break time='120ms' />")
    escaped = escaped.replace("?", "?<break time='100ms' />")
    escaped = escaped.replace(",", ",<break time='80ms' />")
    return escaped


def _rate_percent(rate: int) -> str:
    bounded = max(-10, min(10, rate))
    return f"{bounded * 9:+d}%"


def _pitch_value(pitch: int) -> str:
    bounded = max(-10, min(10, pitch))
    return f"{bounded:+d}st"


def _category_rate_delta(category: str) -> int:
    if category == "joke":
        return 2
    if category == "alert":
        return 1
    if category == "status":
        return -1
    return 0


def _category_pitch_delta(category: str) -> int:
    if category == "joke":
        return 1
    if category == "alert":
        return 1
    if category == "thought":
        return -1
    return 0


def _category_emphasis(category: str) -> str:
    if category in {"joke", "alert", "onboarding"}:
        return "strong"
    if category == "status":
        return "moderate"
    return "reduced"
