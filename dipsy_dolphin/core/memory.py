from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4


MEMORY_SECTIONS = (
    "long_term_facts",
    "preferences",
    "execution_history",
    "tool_context",
)
WRITABLE_MEMORY_SECTIONS = (
    "long_term_facts",
    "preferences",
)
MEMORY_UPDATE_ACTIONS = ("remember", "forget")
MAX_MEMORY_UPDATES_PER_TURN = 3
MAX_MEMORY_ITEMS_PER_SECTION = 20
MAX_INTEREST_ITEMS = 5
DEFAULT_USER_NAME = "friend"


@dataclass(frozen=True)
class MemoryEntry:
    memory_id: str
    value: str
    created_at_utc: str


@dataclass(frozen=True)
class MemoryUpdate:
    action: str
    section: str
    value: str


@dataclass
class AssistantIdentityMemory:
    user_name: str = DEFAULT_USER_NAME
    interests: list[MemoryEntry] = field(default_factory=list)
    has_met_user: bool = False

    def interest_values(self) -> list[str]:
        return [entry.value for entry in self.interests]

    def is_configured(self) -> bool:
        return self.has_met_user or self.user_name != DEFAULT_USER_NAME or bool(self.interests)

    def has_entries(self) -> bool:
        return self.is_configured()


@dataclass
class AssistantMemory:
    identity: AssistantIdentityMemory = field(default_factory=AssistantIdentityMemory)
    long_term_facts: list[MemoryEntry] = field(default_factory=list)
    preferences: list[MemoryEntry] = field(default_factory=list)
    execution_history: list[MemoryEntry] = field(default_factory=list)
    tool_context: list[MemoryEntry] = field(default_factory=list)

    def values_for(self, section: str) -> list[str]:
        return [entry.value for entry in self.entries_for(section)]

    def entries_for(self, section: str) -> list[MemoryEntry]:
        if section not in MEMORY_SECTIONS:
            return []
        return list(getattr(self, section))

    def has_entries(self) -> bool:
        return self.identity.has_entries() or any(
            self.entries_for(section) for section in MEMORY_SECTIONS
        )


def sanitize_memory_updates(payload: object) -> tuple[MemoryUpdate, ...]:
    if not isinstance(payload, list):
        return ()

    updates: list[MemoryUpdate] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        action = normalize_memory_update_action(item.get("action"))
        section = normalize_memory_section(item.get("section"))
        value = normalize_memory_value(item.get("value"))
        if not action or not section or not value:
            continue
        updates.append(MemoryUpdate(action=action, section=section, value=value))
        if len(updates) >= MAX_MEMORY_UPDATES_PER_TURN:
            break
    return tuple(updates)


def apply_memory_updates(
    memory: AssistantMemory,
    updates: Iterable[MemoryUpdate],
) -> AssistantMemory:
    next_memory = replace(memory)
    for section in MEMORY_SECTIONS:
        setattr(next_memory, section, list(memory.entries_for(section)))

    for update in updates:
        if update.section not in WRITABLE_MEMORY_SECTIONS:
            continue
        section_entries = next_memory.entries_for(update.section)
        normalized_value = _normalized_memory_key(update.value)
        filtered = [
            entry
            for entry in section_entries
            if _normalized_memory_key(entry.value) != normalized_value
        ]

        if update.action == "forget":
            setattr(next_memory, update.section, filtered)
            continue

        if update.action != "remember":
            continue

        filtered.append(
            MemoryEntry(
                memory_id=uuid4().hex,
                value=update.value,
                created_at_utc=_utc_now_iso(),
            )
        )
        setattr(next_memory, update.section, filtered[-MAX_MEMORY_ITEMS_PER_SECTION:])

    return next_memory


def clear_memory_section(memory: AssistantMemory, section: str) -> AssistantMemory:
    if section not in MEMORY_SECTIONS:
        return memory
    next_memory = replace(memory)
    setattr(next_memory, section, [])
    return next_memory


def clear_identity_memory(memory: AssistantMemory) -> AssistantMemory:
    next_memory = replace(memory)
    next_memory.identity = AssistantIdentityMemory()
    return next_memory


def migrate_legacy_profile_identity(
    memory: AssistantMemory,
    *,
    user_name: object,
    interests: object,
    has_met_user: object,
) -> tuple[AssistantMemory, bool]:
    next_memory = replace(memory)
    next_memory.identity = replace(memory.identity)
    next_memory.identity.interests = list(memory.identity.interests)

    migrated = False
    current_identity = next_memory.identity
    normalized_name = normalize_user_name(user_name)
    if current_identity.user_name == DEFAULT_USER_NAME and normalized_name != DEFAULT_USER_NAME:
        current_identity.user_name = normalized_name
        migrated = True

    legacy_interests = normalize_interest_values(interests)
    if legacy_interests:
        existing_values = current_identity.interest_values()
        for value in legacy_interests:
            if value in existing_values:
                continue
            current_identity.interests.append(_create_memory_entry(value))
            existing_values.append(value)
            migrated = True
        current_identity.interests = current_identity.interests[-MAX_INTEREST_ITEMS:]

    if bool(has_met_user) and not current_identity.has_met_user:
        current_identity.has_met_user = True
        migrated = True

    if not current_identity.has_met_user and (
        current_identity.user_name != DEFAULT_USER_NAME or bool(current_identity.interests)
    ):
        current_identity.has_met_user = True
        migrated = True

    return next_memory, migrated


def normalize_user_name(value: object) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    return cleaned or DEFAULT_USER_NAME


def normalize_interest_values(values: object) -> list[str]:
    if not isinstance(values, list):
        return []

    normalized: list[str] = []
    for item in values:
        cleaned = str(item or "").strip().lower()
        if not cleaned or cleaned in normalized:
            continue
        normalized.append(cleaned)
        if len(normalized) >= MAX_INTEREST_ITEMS:
            break
    return normalized


def replace_identity_interests(memory: AssistantMemory, values: object) -> AssistantMemory:
    next_memory = replace(memory)
    next_memory.identity = replace(memory.identity)
    next_memory.identity.interests = [
        _create_memory_entry(value) for value in normalize_interest_values(values)
    ]
    return next_memory


def normalize_memory_section(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in MEMORY_SECTIONS:
        return cleaned
    return ""


def normalize_memory_update_action(value: object) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned in MEMORY_UPDATE_ACTIONS:
        return cleaned
    return ""


def normalize_memory_value(value: object) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    if len(cleaned) < 3:
        return ""
    return cleaned[:160]


def summarize_memory(memory: AssistantMemory) -> dict[str, list[str]]:
    return {section: memory.values_for(section) for section in MEMORY_SECTIONS}


def _normalized_memory_key(value: str) -> str:
    return " ".join(value.lower().split())


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _create_memory_entry(value: str) -> MemoryEntry:
    return MemoryEntry(
        memory_id=uuid4().hex,
        value=value,
        created_at_utc=_utc_now_iso(),
    )
