import json
from datetime import datetime, timezone
from pathlib import Path

from ..core.memory import (
    AssistantIdentityMemory,
    AssistantMemory,
    MEMORY_SECTIONS,
    MemoryEntry,
    normalize_interest_values,
    normalize_user_name,
)
from .profile_store import DATA_DIR_NAME, default_app_data_dir


MEMORY_FILE_NAME = "memory.json"


class MemoryStore:
    def __init__(self, app_data_dir: Path | None = None) -> None:
        self.app_data_dir = app_data_dir or default_app_data_dir()
        self.data_dir = self.app_data_dir / DATA_DIR_NAME
        self.memory_path = self.data_dir / MEMORY_FILE_NAME

    def load_memory(self) -> AssistantMemory:
        if not self.memory_path.exists():
            return AssistantMemory()

        try:
            payload = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AssistantMemory()

        memory = AssistantMemory(identity=_load_identity(payload.get("identity")))
        for section in MEMORY_SECTIONS:
            setattr(memory, section, _load_entries(payload.get(section)))
        return memory

    def save_memory(self, memory: AssistantMemory) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "memory_version": 2,
            "saved_at_utc": datetime.now(timezone.utc).isoformat(),
            "identity": {
                "user_name": memory.identity.user_name,
                "interests": [
                    {
                        "memory_id": entry.memory_id,
                        "value": entry.value,
                        "created_at_utc": entry.created_at_utc,
                    }
                    for entry in memory.identity.interests
                ],
                "has_met_user": memory.identity.has_met_user,
            },
        }
        for section in MEMORY_SECTIONS:
            payload[section] = [
                {
                    "memory_id": entry.memory_id,
                    "value": entry.value,
                    "created_at_utc": entry.created_at_utc,
                }
                for entry in memory.entries_for(section)
            ]
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.memory_path

    def delete_memory(self) -> None:
        if self.memory_path.exists():
            self.memory_path.unlink()


def _load_entries(payload: object) -> list[MemoryEntry]:
    if not isinstance(payload, list):
        return []

    entries: list[MemoryEntry] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        memory_id = str(item.get("memory_id", "")).strip()
        value = " ".join(str(item.get("value", "")).split()).strip()
        created_at_utc = str(item.get("created_at_utc", "")).strip()
        if not memory_id or not value:
            continue
        entries.append(
            MemoryEntry(
                memory_id=memory_id,
                value=value,
                created_at_utc=created_at_utc,
            )
        )
    return entries


def _load_identity(payload: object) -> AssistantIdentityMemory:
    if not isinstance(payload, dict):
        return AssistantIdentityMemory()

    loaded_interests = _load_entries(payload.get("interests"))
    normalized_values = normalize_interest_values([entry.value for entry in loaded_interests])
    normalized_entries: list[MemoryEntry] = []
    for value in normalized_values:
        matching_entry = next(
            (entry for entry in loaded_interests if entry.value.strip().lower() == value),
            None,
        )
        if matching_entry is None:
            continue
        normalized_entries.append(
            MemoryEntry(
                memory_id=matching_entry.memory_id,
                value=value,
                created_at_utc=matching_entry.created_at_utc,
            )
        )

    identity = AssistantIdentityMemory(
        user_name=normalize_user_name(payload.get("user_name", "friend")),
        interests=normalized_entries,
        has_met_user=bool(payload.get("has_met_user", False)),
    )
    return identity
