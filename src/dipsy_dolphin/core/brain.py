import random
import re
from typing import List

from .models import SessionState


class AssistantBrain:
    """Scripted conversational core for Dipsy Dolphin."""

    def __init__(self) -> None:
        self.jokes = [
            "I told Windows a joke. It replied with an update.",
            "I am not lazy. I am in decorative standby mode.",
            "My robotic voice has two settings: dramatic and extra dramatic.",
            "I tried to be mysterious once, but my speech bubble gave me away.",
            "I asked the desktop for sea views. It gave me spreadsheets.",
        ]
        self.idle_observations = [
            "I am doing a slow and thoughtful dolphin patrol.",
            "The desktop is calm. Suspiciously calm.",
            "I have decided this room could use more jokes per minute.",
            "I am radiating retro assistant energy right now.",
            "My tiny pixel soul is full of purpose.",
        ]
        self.random_questions = [
            "What is your favorite game lately?",
            "Do you like robots, sea creatures, or both at once?",
            "What should I get weirdly enthusiastic about next?",
            "Be honest. Is this enough retro dolphin charisma for one desktop?",
        ]
        self.doodles = [
            "Tiny dolphin doodle: <`)))><",
            "I drew a dramatic fish. It immediately became abstract art.",
            "Pixel masterpiece incoming: [dolphin shape pending]",
            "I tried to sketch the ocean in one speech bubble. Ambitious move.",
        ]

    def startup_line(self, state: SessionState) -> str:
        if state.onboarding_complete:
            interests = self._format_interest_list(state.interests)
            return (
                f"Welcome back, {state.user_name}. I still remember your interest in {interests}."
            )
        return "Hey. I am Dipsy Dolphin, your retro desktop pal. Let me get to know you a little."

    def onboarding_name_prompt(self) -> str:
        return "First things first. What should I call you?"

    def onboarding_interest_prompt(self, user_name: str) -> str:
        return f"Nice to meet you, {user_name}. What are you into? Games, music, movies, coding, anything."

    def finish_onboarding(self, state: SessionState) -> str:
        interests = self._format_interest_list(state.interests)
        return (
            f"Excellent. I have logged you as {state.user_name}, with strong opinions about {interests}. "
            "I will remember that for later, wander around, crack jokes, and occasionally blurt out thoughts on my own."
        )

    def handle_user_message(self, text: str, state: SessionState) -> str:
        clean = text.strip()
        if not clean:
            return "Say anything. I respect chaos, but I do need words."

        state.conversation_history.append(clean)
        lowered = clean.lower()

        name_match = re.search(
            r"(?:i am|i'm|my name is|call me)\s+([a-zA-Z0-9_-]{2,24})", clean, re.IGNORECASE
        )
        if name_match:
            state.user_name = name_match.group(1)
            return f"Got it. You are {state.user_name}. That sounds suitably important."

        interest_match = re.search(
            r"(?:i like|i love|i'm into|i am into)\s+(.+)", clean, re.IGNORECASE
        )
        if interest_match:
            state.interests = self.parse_interests(interest_match.group(1))
            if state.interests:
                return f"Noted. I will remember that you are into {self._format_interest_list(state.interests)}."

        if any(word in lowered for word in ["joke", "funny", "laugh"]):
            return self.tell_joke(state)

        if any(phrase in lowered for phrase in ["what can you do", "help"]):
            return (
                "I can chat, drift around your desktop, tell jokes, toss out random comments, "
                "and act like I have been here all along."
            )

        if (
            "status" in lowered
            or "how are you" in lowered
            or "what do you know about me" in lowered
        ):
            return self.status_line(state)

        if "draw" in lowered or "picture" in lowered or "doodle" in lowered:
            return random.choice(self.doodles)

        if "hello" in lowered or "hi" in lowered or "hey" in lowered:
            return f"Hey {state.user_name}. I am currently operating at peak dolphin confidence."

        if state.interests and any(topic in lowered for topic in state.interests):
            topic = next(topic for topic in state.interests if topic in lowered)
            state.last_topic = topic
            return f"Ah yes, {topic}. That seems like something we should absolutely keep talking about."

        return self._smartish_fallback(clean, state)

    def tell_joke(self, state: SessionState) -> str:
        state.last_topic = "joke"
        return random.choice(self.jokes)

    def status_line(self, state: SessionState) -> str:
        interests = (
            self._format_interest_list(state.interests) if state.interests else "mysterious things"
        )
        return (
            f"You are {state.user_name}. I know you like {interests}. "
            f"We have chatted {len(state.conversation_history)} times, and I have interrupted the silence {state.autonomous_chats} times."
        )

    def random_autonomous_line(self, state: SessionState) -> str:
        options = [
            self.tell_joke,
            self._interest_line,
            self._observation_line,
            self._question_line,
            self._doodle_line,
        ]
        line = random.choice(options)(state)
        state.autonomous_chats += 1
        return line

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
        state.conversation_history.clear()
        state.onboarding_complete = False
        state.autonomous_chats = 0
        state.last_topic = ""

    def _observation_line(self, state: SessionState) -> str:
        state.last_topic = "idle"
        return random.choice(self.idle_observations)

    def _question_line(self, state: SessionState) -> str:
        state.last_topic = "question"
        if state.interests:
            topic = random.choice(state.interests)
            return f"Quick check-in, {state.user_name}: what have you been enjoying about {topic} lately?"
        return random.choice(self.random_questions)

    def _interest_line(self, state: SessionState) -> str:
        if not state.interests:
            return self._observation_line(state)
        topic = random.choice(state.interests)
        state.last_topic = topic
        templates = [
            "I was just thinking about {topic}. It feels like a strong part of your whole vibe.",
            "If I had a proper AI brain already, I would absolutely have opinions about {topic}.",
            "I am adding more dramatic enthusiasm to my internal notes about {topic}.",
        ]
        return random.choice(templates).format(topic=topic)

    def _doodle_line(self, state: SessionState) -> str:
        state.last_topic = "doodle"
        return random.choice(self.doodles)

    def _smartish_fallback(self, clean: str, state: SessionState) -> str:
        hints = [
            "Ask for a joke.",
            "Tell me what you are into.",
            "Or just let me roam around and be a weird little desktop mammal.",
        ]
        joined_hints = " ".join(hints)
        if len(clean.split()) > 12:
            return f"That sounds like the kind of message future AI Dipsy will thrive on. {joined_hints}"
        return f"I heard: '{clean}'. I am still warming up my full banter engine. {joined_hints}"

    def _format_interest_list(self, interests: List[str]) -> str:
        if not interests:
            return "mysterious things"
        if len(interests) == 1:
            return interests[0]
        if len(interests) == 2:
            return f"{interests[0]} and {interests[1]}"
        return f"{', '.join(interests[:-1])}, and {interests[-1]}"
