import json

from dipsy_dolphin.core.models import UserProfile
from dipsy_dolphin.storage.profile_store import ProfileStore
from dipsy_dolphin.voice.models import VoiceSettings


def test_profile_store_round_trips_profile_data(tmp_path) -> None:
    store = ProfileStore(app_data_dir=tmp_path)
    profile = UserProfile(
        autonomy_enabled=False,
        autonomy_pace="lively",
        voice=VoiceSettings(enabled=False, voice_id="Microsoft Sam", rate=3, volume=80, pitch=-2),
    )

    saved_path = store.save_profile(profile)
    loaded_profile = store.load_profile()

    assert saved_path.exists()
    assert loaded_profile == profile


def test_profile_store_ignores_invalid_payload(tmp_path) -> None:
    store = ProfileStore(app_data_dir=tmp_path)
    store.data_dir.mkdir(parents=True, exist_ok=True)
    store.profile_path.write_text(
        json.dumps({"user_name": 123, "interests": "nope"}), encoding="utf-8"
    )

    loaded_profile = store.load_profile()

    assert loaded_profile.user_name == "123"
    assert loaded_profile.interests == []
    assert loaded_profile.has_met_user is False
    assert loaded_profile.autonomy_enabled is True
    assert loaded_profile.autonomy_pace == "normal"
    assert loaded_profile.voice == VoiceSettings()


def test_profile_store_omits_identity_fields_when_saving(tmp_path) -> None:
    store = ProfileStore(app_data_dir=tmp_path)
    profile = UserProfile(
        user_name="Taylor",
        interests=["coding", "music"],
        has_met_user=True,
        autonomy_enabled=False,
        autonomy_pace="quiet",
    )

    saved_path = store.save_profile(profile)
    payload = json.loads(saved_path.read_text(encoding="utf-8"))

    assert "user_name" not in payload
    assert "interests" not in payload
    assert "has_met_user" not in payload
    assert payload["autonomy_enabled"] is False
    assert payload["autonomy_pace"] == "quiet"
    assert payload["voice"] == {
        "enabled": True,
        "profile": "retro_classic",
        "voice_id": "",
        "rate": 1,
        "volume": 100,
        "pitch": -1,
    }
