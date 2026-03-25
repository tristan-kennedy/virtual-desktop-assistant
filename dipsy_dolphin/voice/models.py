from __future__ import annotations

from dataclasses import dataclass


VOICE_PROFILE_VALUES = ("retro_classic",)
SPEECH_EVENT_TYPES = (
    "voice_selected",
    "started",
    "word",
    "finished",
    "cancelled",
    "failed",
)


def _bounded_int(value: object, *, minimum: int, maximum: int, fallback: int) -> int:
    if not isinstance(value, (int, float, str)):
        return fallback
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, number))


def normalize_voice_profile(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in VOICE_PROFILE_VALUES:
        return cleaned
    return "retro_classic"


@dataclass(frozen=True)
class VoiceSettings:
    enabled: bool = True
    profile: str = "retro_classic"
    voice_id: str = ""
    rate: int = 1
    volume: int = 100
    pitch: int = -1

    def bounded(self) -> VoiceSettings:
        return VoiceSettings(
            enabled=bool(self.enabled),
            profile=normalize_voice_profile(self.profile),
            voice_id=str(self.voice_id or "").strip(),
            rate=_bounded_int(self.rate, minimum=-10, maximum=10, fallback=1),
            volume=_bounded_int(self.volume, minimum=0, maximum=100, fallback=100),
            pitch=_bounded_int(self.pitch, minimum=-10, maximum=10, fallback=-1),
        )


def coerce_voice_settings(payload: object) -> VoiceSettings:
    if not isinstance(payload, dict):
        return VoiceSettings()
    return VoiceSettings(
        enabled=bool(payload.get("enabled", True)),
        profile=str(payload.get("profile", "retro_classic")),
        voice_id=str(payload.get("voice_id", "")).strip(),
        rate=payload.get("rate", 1),
        volume=payload.get("volume", 100),
        pitch=payload.get("pitch", -1),
    ).bounded()


@dataclass(frozen=True)
class VoiceOption:
    voice_id: str
    name: str
    culture: str = ""
    gender: str = ""
    age: str = ""
    description: str = ""


@dataclass(frozen=True)
class VoiceSelection:
    option: VoiceOption | None
    used_fallback: bool = False
    reason: str = ""


@dataclass(frozen=True)
class SpeechRequest:
    utterance_id: str
    text: str
    category: str = "normal"
    settings: VoiceSettings = VoiceSettings()


@dataclass(frozen=True)
class SpeechEvent:
    utterance_id: str
    event_type: str
    word: str = ""
    char_index: int = 0
    char_length: int = 0
    completed: bool = False
    message: str = ""
    voice_id: str = ""
    voice_name: str = ""
    used_fallback: bool = False
