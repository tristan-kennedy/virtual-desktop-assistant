from dataclasses import dataclass, field
from typing import List


@dataclass
class ConversationTurn:
    role: str
    content: str


@dataclass
class UserProfile:
    user_name: str = "friend"
    interests: List[str] = field(default_factory=list)
    has_met_user: bool = False

    def is_configured(self) -> bool:
        return self.has_met_user or self.user_name != "friend" or bool(self.interests)


@dataclass
class SessionState:
    profile: UserProfile = field(default_factory=UserProfile)
    conversation_history: List[str] = field(default_factory=list)
    turns: List[ConversationTurn] = field(default_factory=list)
    onboarding_complete: bool = False
    autonomous_chats: int = 0
    last_topic: str = ""
    last_assistant_line: str = ""
    autonomy_cooldown_ms: int = 0

    def __post_init__(self) -> None:
        self.onboarding_complete = self.onboarding_complete or self.profile.is_configured()

    @property
    def user_name(self) -> str:
        return self.profile.user_name

    @user_name.setter
    def user_name(self, value: str) -> None:
        cleaned = value.strip()
        self.profile.user_name = cleaned or "friend"

    @property
    def interests(self) -> List[str]:
        return self.profile.interests

    @interests.setter
    def interests(self, value: List[str]) -> None:
        self.profile.interests = value

    def apply_profile(self, profile: UserProfile) -> None:
        self.profile = profile
        self.onboarding_complete = profile.is_configured()

    def mark_profile_configured(self) -> None:
        if not self.profile.is_configured():
            return
        self.profile.has_met_user = True
        self.onboarding_complete = True

    def remember_user_turn(self, text: str) -> None:
        self.conversation_history.append(text)
        self.turns.append(ConversationTurn(role="user", content=text))

    def remember_assistant_turn(self, text: str) -> None:
        self.last_assistant_line = text
        self.turns.append(ConversationTurn(role="assistant", content=text))
