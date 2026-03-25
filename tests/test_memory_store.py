import json

from dipsy_dolphin.core.memory import AssistantIdentityMemory, AssistantMemory, MemoryEntry
from dipsy_dolphin.storage.memory_store import MemoryStore


def test_memory_store_round_trips_memory(tmp_path) -> None:
    store = MemoryStore(app_data_dir=tmp_path)
    memory = AssistantMemory(
        identity=AssistantIdentityMemory(
            user_name="Taylor",
            interests=[
                MemoryEntry(
                    memory_id="interest-1",
                    value="coding",
                    created_at_utc="2026-03-24T00:00:02Z",
                )
            ],
            has_met_user=True,
        ),
        long_term_facts=[
            MemoryEntry(
                memory_id="fact-1", value="lives in Seattle", created_at_utc="2026-03-24T00:00:00Z"
            )
        ],
        preferences=[
            MemoryEntry(
                memory_id="pref-1", value="likes shopping", created_at_utc="2026-03-24T00:00:01Z"
            )
        ],
    )

    saved_path = store.save_memory(memory)
    loaded = store.load_memory()

    assert saved_path.exists()
    assert loaded == memory


def test_memory_store_ignores_invalid_payload(tmp_path) -> None:
    store = MemoryStore(app_data_dir=tmp_path)
    store.data_dir.mkdir(parents=True, exist_ok=True)
    store.memory_path.write_text(json.dumps({"long_term_facts": "bad"}), encoding="utf-8")

    loaded = store.load_memory()

    assert loaded.long_term_facts == []
    assert loaded.preferences == []
    assert loaded.identity.user_name == "friend"
    assert loaded.identity.interests == []


def test_memory_store_loads_identity_payload(tmp_path) -> None:
    store = MemoryStore(app_data_dir=tmp_path)
    store.data_dir.mkdir(parents=True, exist_ok=True)
    store.memory_path.write_text(
        json.dumps(
            {
                "identity": {
                    "user_name": "Taylor",
                    "interests": [
                        {
                            "memory_id": "interest-1",
                            "value": "Coding",
                            "created_at_utc": "2026-03-24T00:00:00Z",
                        }
                    ],
                    "has_met_user": True,
                }
            }
        ),
        encoding="utf-8",
    )

    loaded = store.load_memory()

    assert loaded.identity.user_name == "Taylor"
    assert loaded.identity.interest_values() == ["coding"]
    assert loaded.identity.has_met_user is True


def test_memory_store_delete_removes_file(tmp_path) -> None:
    store = MemoryStore(app_data_dir=tmp_path)
    store.save_memory(AssistantMemory())

    store.delete_memory()

    assert not store.memory_path.exists()
