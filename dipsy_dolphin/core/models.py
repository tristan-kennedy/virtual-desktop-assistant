from dataclasses import dataclass, field
from typing import List

from .emotion import EmotionState, seed_emotion_state
from .memory import (
    AssistantMemory,
    DEFAULT_USER_NAME,
    normalize_user_name,
    replace_identity_interests,
)
from ..voice.models import VoiceSettings, coerce_voice_settings


AUTONOMY_PACE_VALUES = ("quiet", "normal", "lively")


def normalize_autonomy_pace(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in AUTONOMY_PACE_VALUES:
        return cleaned
    return "normal"


@dataclass
class ConversationTurn:
    role: str
    content: str


@dataclass
class UserProfile:
    user_name: str = "friend"
    interests: List[str] = field(default_factory=list)
    has_met_user: bool = False
    autonomy_enabled: bool = True
    autonomy_pace: str = "normal"
    voice: VoiceSettings = field(default_factory=VoiceSettings)

    def is_configured(self) -> bool:
        return self.has_met_user or self.user_name != "friend" or bool(self.interests)

    def __post_init__(self) -> None:
        self.voice = coerce_voice_settings(
            {
                "enabled": self.voice.enabled,
                "profile": self.voice.profile,
                "voice_id": self.voice.voice_id,
                "rate": self.voice.rate,
                "volume": self.voice.volume,
                "pitch": self.voice.pitch,
            }
        )


@dataclass
class SessionState:
    profile: UserProfile = field(default_factory=UserProfile)
    turns: List[ConversationTurn] = field(default_factory=list)
    memory: AssistantMemory = field(default_factory=AssistantMemory)
    emotion: EmotionState = field(default_factory=EmotionState)
    onboarding_complete: bool = False
    last_user_interaction_ms: int = 0
    autonomous_chats: int = 0
    autonomous_beats: int = 0
    consecutive_silent_autonomous_turns: int = 0
    last_autonomous_behavior: str = ""
    recent_autonomous_behaviors: List[str] = field(default_factory=list)
    last_topic: str = ""
    last_assistant_line: str = ""
    last_scene_kind: str = ""
    recent_scene_kinds: List[str] = field(default_factory=list)
    scene_kind_times_ms: dict[str, int] = field(default_factory=dict)
    last_autonomous_at_ms: int = 0
    autonomous_behavior_times_ms: dict[str, int] = field(default_factory=dict)
    autonomy_cooldown_ms: int = 0

    def __post_init__(self) -> None:
        self.onboarding_complete = (
            self.onboarding_complete
            or self.memory.identity.is_configured()
            or self.profile.is_configured()
        )
        self.profile.autonomy_pace = normalize_autonomy_pace(self.profile.autonomy_pace)
        has_met_user, user_name, interests_count = self._identity_seed_values()
        self.emotion = seed_emotion_state(
            has_met_user=has_met_user,
            user_name=user_name,
            interests_count=interests_count,
            base=self.emotion,
        )

    @property
    def user_name(self) -> str:
        identity = self.memory.identity
        if identity.is_configured() or not self.profile.is_configured():
            return identity.user_name
        return self.profile.user_name

    @user_name.setter
    def user_name(self, value: str) -> None:
        self.memory.identity.user_name = normalize_user_name(value)

    @property
    def interests(self) -> List[str]:
        identity = self.memory.identity
        if identity.is_configured() or not self.profile.is_configured():
            return identity.interest_values()
        return self.profile.interests

    @interests.setter
    def interests(self, value: List[str]) -> None:
        self.memory = replace_identity_interests(self.memory, value)

    def apply_profile(self, profile: UserProfile) -> None:
        self.profile = profile
        self.profile.autonomy_pace = normalize_autonomy_pace(self.profile.autonomy_pace)
        self.onboarding_complete = self.memory.identity.is_configured() or profile.is_configured()
        has_met_user, user_name, interests_count = self._identity_seed_values()
        self.emotion = seed_emotion_state(
            has_met_user=has_met_user,
            user_name=user_name,
            interests_count=interests_count,
            base=self.emotion,
        )

    def mark_profile_configured(self) -> None:
        if not self.memory.identity.is_configured() and self.profile.is_configured():
            self.memory.identity.user_name = normalize_user_name(self.profile.user_name)
            self.memory = replace_identity_interests(self.memory, self.profile.interests)
        if self.user_name == DEFAULT_USER_NAME and not self.interests:
            return
        self.memory.identity.has_met_user = True
        self.onboarding_complete = True
        has_met_user, user_name, interests_count = self._identity_seed_values()
        self.emotion = seed_emotion_state(
            has_met_user=has_met_user,
            user_name=user_name,
            interests_count=interests_count,
            base=self.emotion,
        )

    def remember_user_turn(self, text: str) -> None:
        self.turns.append(ConversationTurn(role="user", content=text))

    def remember_assistant_turn(self, text: str) -> None:
        self.last_assistant_line = text
        self.turns.append(ConversationTurn(role="assistant", content=text))

    def mark_user_interaction(self, now_ms: int) -> None:
        self.last_user_interaction_ms = max(0, now_ms)

    def remember_autonomous_behavior(self, behavior: str) -> None:
        cleaned = behavior.strip().lower()
        if not cleaned:
            return
        self.last_autonomous_behavior = cleaned
        self.recent_autonomous_behaviors.append(cleaned)
        if len(self.recent_autonomous_behaviors) > 6:
            self.recent_autonomous_behaviors = self.recent_autonomous_behaviors[-6:]

    def record_autonomous_timing(self, behavior: str, now_ms: int) -> None:
        cleaned = behavior.strip().lower()
        if not cleaned:
            return
        clamped_now_ms = max(0, now_ms)
        self.last_autonomous_at_ms = clamped_now_ms
        self.autonomous_behavior_times_ms[cleaned] = clamped_now_ms

    def remember_scene_kind(self, scene_kind: str, now_ms: int) -> None:
        cleaned = str(scene_kind or "").strip().lower()
        if not cleaned:
            return
        clamped_now_ms = max(0, now_ms)
        self.last_scene_kind = cleaned
        self.recent_scene_kinds.append(cleaned)
        if len(self.recent_scene_kinds) > 6:
            self.recent_scene_kinds = self.recent_scene_kinds[-6:]
        self.scene_kind_times_ms[cleaned] = clamped_now_ms

    def _identity_seed_values(self) -> tuple[bool, str, int]:
        identity = self.memory.identity
        if identity.is_configured() or not self.profile.is_configured():
            return (
                identity.has_met_user,
                identity.user_name,
                len(identity.interests),
            )
        return (
            self.profile.has_met_user,
            self.profile.user_name,
            len(self.profile.interests),
        )
