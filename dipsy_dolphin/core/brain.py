import re
from typing import List

from .emotion import EmotionState
from .memory import AssistantMemory
from .models import SessionState


class AssistantBrain:
    """Profile and session helper for the LLM-driven controller."""

    def parse_interests(self, raw_text: str) -> List[str]:
        cleaned = raw_text.strip().strip(".?!")
        if not cleaned:
            return []

        normalized = re.sub(r"\band\b", ",", cleaned, flags=re.IGNORECASE)
        parts = [part.strip(" .,!?").lower() for part in normalized.split(",")]
        interests: List[str] = []
        for part in parts:
            if not part:
                continue
            if part in {"stuff", "things", "anything", "everything"}:
                continue
            if part not in interests:
                interests.append(part)
        return interests[:5]

    def reset_state(self, state: SessionState) -> None:
        state.user_name = "friend"
        state.interests.clear()
        state.profile.has_met_user = False
        state.profile.user_name = "friend"
        state.profile.interests.clear()
        state.turns.clear()
        state.memory = AssistantMemory()
        state.onboarding_complete = False
        state.last_user_interaction_ms = 0
        state.autonomous_chats = 0
        state.autonomous_beats = 0
        state.last_autonomous_behavior = ""
        state.recent_autonomous_behaviors.clear()
        state.last_topic = ""
        state.last_assistant_line = ""
        state.last_autonomous_at_ms = 0
        state.autonomous_behavior_times_ms.clear()
        state.autonomy_cooldown_ms = 0
        state.emotion = EmotionState()

    def apply_profile_updates(self, text: str, state: SessionState) -> bool:
        updated = False

        extracted_name = self._extract_name(text)
        if extracted_name:
            state.user_name = extracted_name
            updated = True

        interest_text = self._extract_interest_text(text)
        if interest_text:
            parsed = self.parse_interests(interest_text)
            if parsed:
                state.interests = parsed
                updated = True

        if updated:
            state.mark_profile_configured()

        return updated

    def _extract_name(self, text: str) -> str:
        name_match = re.search(
            r"(?:i am|i'm|my name is|call me)\s+([a-zA-Z0-9_-]{2,24})", text, re.IGNORECASE
        )
        if not name_match:
            return ""
        return name_match.group(1)

    def _extract_interest_text(self, text: str) -> str:
        interest_match = re.search(
            r"(?:i like|i love|i'm into|i am into)\s+(.+)", text, re.IGNORECASE
        )
        if not interest_match:
            return ""
        return interest_match.group(1)
