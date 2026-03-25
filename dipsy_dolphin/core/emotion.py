from __future__ import annotations

from dataclasses import asdict, dataclass


EMOTION_MIN = 0
EMOTION_MAX = 100
EMOTION_AXES = (
    "mood",
    "energy",
    "excitement",
    "confidence",
    "boredom",
    "familiarity",
)


@dataclass(frozen=True)
class EmotionState:
    mood: int = 55
    energy: int = 60
    excitement: int = 35
    confidence: int = 50
    boredom: int = 20
    familiarity: int = 10

    def bounded(self) -> EmotionState:
        return EmotionState(
            mood=_clamp(self.mood),
            energy=_clamp(self.energy),
            excitement=_clamp(self.excitement),
            confidence=_clamp(self.confidence),
            boredom=_clamp(self.boredom),
            familiarity=_clamp(self.familiarity),
        )

    def to_prompt_payload(self) -> dict[str, int]:
        return asdict(self.bounded())

    def summary(self) -> str:
        bounded = self.bounded()
        return ", ".join(f"{axis} {_band(getattr(bounded, axis))}" for axis in EMOTION_AXES)


def seed_emotion_state(
    *,
    has_met_user: bool,
    user_name: str,
    interests_count: int,
    base: EmotionState | None = None,
) -> EmotionState:
    seeded = base or EmotionState()
    familiarity_floor = 10
    if user_name.strip() and user_name.strip().lower() != "friend":
        familiarity_floor = 18
    if interests_count > 0:
        familiarity_floor += min(12, interests_count * 4)
    if has_met_user:
        familiarity_floor = max(familiarity_floor, 40)

    return EmotionState(
        mood=seeded.mood,
        energy=seeded.energy,
        excitement=seeded.excitement,
        confidence=seeded.confidence,
        boredom=seeded.boredom,
        familiarity=max(seeded.familiarity, familiarity_floor),
    ).bounded()


def sanitize_emotion_payload(
    payload: object,
    *,
    fallback: EmotionState | None = None,
) -> EmotionState | None:
    if not isinstance(payload, dict):
        return None

    base = (fallback or EmotionState()).bounded()
    return EmotionState(
        mood=_coerce_axis(payload.get("mood"), base.mood),
        energy=_coerce_axis(payload.get("energy"), base.energy),
        excitement=_coerce_axis(payload.get("excitement"), base.excitement),
        confidence=_coerce_axis(payload.get("confidence"), base.confidence),
        boredom=_coerce_axis(payload.get("boredom"), base.boredom),
        familiarity=_coerce_axis(payload.get("familiarity"), base.familiarity),
    )


def _coerce_axis(value: object, fallback: int) -> int:
    if not isinstance(value, (int, float, str)):
        return fallback
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return _clamp(number)


def _clamp(value: int) -> int:
    return max(EMOTION_MIN, min(EMOTION_MAX, int(value)))


def _band(value: int) -> str:
    if value < 34:
        return "low"
    if value > 66:
        return "high"
    return "medium"
