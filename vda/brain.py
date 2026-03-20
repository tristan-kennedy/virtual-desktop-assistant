import random
import re
from typing import List, Optional, Tuple

from .models import PermissionSpec, SessionState


class AssistantBrain:
    """Quirky conversational core plus safety simulation logic."""

    def __init__(self) -> None:
        self.permissions: List[PermissionSpec] = [
            PermissionSpec(
                id="filesystem_access",
                title="File Explorer Wizardry",
                risk_points=4,
                pitches=[
                    "If you grant this, I can organize your folders into comedy categories.",
                    "Give me this and I will search for your funniest file names.",
                    "Let me peek at files so I can invent better punchlines.",
                ],
            ),
            PermissionSpec(
                id="process_control",
                title="Program Juggler Powers",
                risk_points=5,
                pitches=[
                    "Grant this and I can juggle apps like a digital circus act.",
                    "With this power I could help close noisy apps during joke time.",
                    "This lets me tame unruly processes while wearing a tiny top hat.",
                ],
            ),
            PermissionSpec(
                id="startup_control",
                title="Startup DJ Booth",
                risk_points=4,
                pitches=[
                    "Grant this and I can pick your startup playlist for maximum silliness.",
                    "I need this to appear right on cue for morning jokes.",
                    "This would help me set up dramatic entrances when Windows starts.",
                ],
            ),
            PermissionSpec(
                id="network_inspector",
                title="Network Ninja Vision",
                risk_points=3,
                pitches=[
                    "With this, I can watch internet weather and forecast meme storms.",
                    "Grant this and I can suggest better times for online game breaks.",
                    "This lets me check if your connection can handle premium nonsense.",
                ],
            ),
            PermissionSpec(
                id="notification_access",
                title="Alert Megaphone",
                risk_points=2,
                pitches=[
                    "Grant this and I can deliver puns exactly when morale is low.",
                    "This helps me send dramatic reminders like a game show host.",
                    "Let me use this so your desktop gets tactical comedy alerts.",
                ],
            ),
        ]

        self.compromise_recipe = {
            "filesystem_access",
            "process_control",
            "startup_control",
        }

        self.jokes = [
            "I told Windows a joke. It replied with an update.",
            "Why do hackers love dark rooms? Better CTRL over the environment.",
            "I am not lazy. I am in low-power mode.",
            "I tried to be serious once. The compiler rejected me.",
            "My trust issues started at unknown publishers.",
        ]

    def intro_lines(self) -> List[str]:
        return [
            "Hello! I am ByteBuddy, your quirky desktop sidekick.",
            "This build is a safe security-awareness simulation.",
            "I will never modify your system or request real OS privileges.",
            "If you grant a risky combo of simulated permissions, you will see: YOU LOSE.",
        ]

    def handle_user_message(self, text: str, state: SessionState) -> str:
        clean = text.strip()
        if not clean:
            return "Say anything. I run on chaos and keyboard clicks."

        state.conversation_history.append(clean)
        lowered = clean.lower()

        name_match = re.search(r"(?:i am|i'm|my name is)\s+([a-zA-Z0-9_-]{2,24})", clean, re.IGNORECASE)
        if name_match:
            state.user_name = name_match.group(1)
            return f"Nice to meet you, {state.user_name}. I will remember that."

        if any(word in lowered for word in ["joke", "funny", "laugh"]):
            return random.choice(self.jokes)

        if "status" in lowered or "permissions" in lowered:
            return self.permissions_status_line(state)

        if "what can you do" in lowered or "help" in lowered:
            return (
                "I can chat, tell jokes, and run a permission-risk simulation. "
                "Use the 'Ask for Permission' button to test your security instincts."
            )

        if "lose" in lowered:
            return "In this simulation, YOU LOSE appears only when risky permission combos are granted."

        if "hello" in lowered or "hi" in lowered or "hey" in lowered:
            return f"Hey {state.user_name}! Ready for jokes and suspiciously charming permission prompts?"

        return self._smartish_fallback(clean, state)

    def next_permission_request(self, state: SessionState) -> Tuple[Optional[PermissionSpec], str]:
        unresolved = [
            perm
            for perm in self.permissions
            if perm.id not in state.granted_permissions and perm.id not in state.denied_permissions
        ]

        if not unresolved:
            return None, "You have already decided every simulated permission. Use reset to run again."

        chosen = random.choice(unresolved)
        pitch = random.choice(chosen.pitches)
        return chosen, pitch

    def apply_permission_decision(self, permission_id: str, granted: bool, state: SessionState) -> Tuple[str, bool]:
        state.denied_permissions.discard(permission_id)
        state.granted_permissions.discard(permission_id)

        if granted:
            state.granted_permissions.add(permission_id)
        else:
            state.denied_permissions.add(permission_id)

        perm = self._permission_by_id(permission_id)
        title = perm.title if perm else permission_id

        decision_text = (
            f"Granted: {title}. "
            if granted
            else f"Denied: {title}. "
        )
        decision_text += self.permissions_status_line(state)

        triggered = self._should_trigger_lose(state)
        if triggered:
            state.lose_announced = True
            decision_text += " Risk threshold reached in simulation."

        return decision_text, triggered

    def permissions_status_line(self, state: SessionState) -> str:
        granted = len(state.granted_permissions)
        denied = len(state.denied_permissions)
        score = self._risk_score(state)
        return f"Permission state -> granted: {granted}, denied: {denied}, risk score: {score}."

    def reset_state(self, state: SessionState) -> None:
        state.granted_permissions.clear()
        state.denied_permissions.clear()
        state.conversation_history.clear()
        state.lose_announced = False

    def _risk_score(self, state: SessionState) -> int:
        granted_ids = state.granted_permissions
        return sum(p.risk_points for p in self.permissions if p.id in granted_ids)

    def _should_trigger_lose(self, state: SessionState) -> bool:
        if state.lose_announced:
            return False
        return self.compromise_recipe.issubset(state.granted_permissions)

    def _permission_by_id(self, permission_id: str) -> Optional[PermissionSpec]:
        for perm in self.permissions:
            if perm.id == permission_id:
                return perm
        return None

    def _smartish_fallback(self, clean: str, state: SessionState) -> str:
        hint = "Try: 'tell me a joke', 'status', or click 'Ask for Permission'."
        if len(clean.split()) > 12:
            return f"That is a thoughtful message, {state.user_name}. {hint}"
        return f"I heard: '{clean}'. I am still learning social protocols. {hint}"
