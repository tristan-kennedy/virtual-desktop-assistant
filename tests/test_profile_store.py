import json

from dipsy_dolphin.core.models import UserProfile
from dipsy_dolphin.storage.profile_store import ProfileStore


def test_profile_store_round_trips_profile_data(tmp_path) -> None:
    store = ProfileStore(app_data_dir=tmp_path)
    profile = UserProfile(user_name="Taylor", interests=["coding", "music"], has_met_user=True)

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
