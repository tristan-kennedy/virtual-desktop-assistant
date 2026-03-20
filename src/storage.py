import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .models import UserProfile


APP_DIR_NAME = "DipsyDolphin"
DATA_DIR_NAME = "data"
PROFILE_FILE_NAME = "profile.json"


def default_app_data_dir() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / APP_DIR_NAME
    return Path.home() / "AppData" / "Local" / APP_DIR_NAME


class ProfileStore:
    def __init__(self, app_data_dir: Path | None = None) -> None:
        self.app_data_dir = app_data_dir or default_app_data_dir()
        self.data_dir = self.app_data_dir / DATA_DIR_NAME
        self.profile_path = self.data_dir / PROFILE_FILE_NAME

    def load_profile(self) -> UserProfile:
        if not self.profile_path.exists():
            return UserProfile()

        try:
            payload = json.loads(self.profile_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return UserProfile()

        user_name_raw = payload.get("user_name", "friend")
        user_name = str(user_name_raw).strip() or "friend"

        interests_raw = payload.get("interests", [])
        interests = []
        if isinstance(interests_raw, list):
            for item in interests_raw:
                cleaned = str(item).strip().lower()
                if cleaned and cleaned not in interests:
                    interests.append(cleaned)

        has_met_user = bool(payload.get("has_met_user", False))
        return UserProfile(user_name=user_name, interests=interests, has_met_user=has_met_user)

    def save_profile(self, profile: UserProfile) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "profile_version": 1,
            "saved_at_utc": datetime.now(timezone.utc).isoformat(),
            "user_name": profile.user_name,
            "interests": profile.interests,
            "has_met_user": profile.has_met_user,
        }
        self.profile_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.profile_path

    def delete_profile(self) -> None:
        if self.profile_path.exists():
            self.profile_path.unlink()
