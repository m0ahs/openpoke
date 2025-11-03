"""User profile storage and retrieval."""

import json
import threading
from pathlib import Path
from typing import Dict, Optional

from ..logging_config import logger

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PROFILE_PATH = _DATA_DIR / "user_profile.json"


class UserProfile:
    """Simple file-based user profile storage."""

    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("user profile directory creation failed", extra={"error": str(exc)})

    def save(self, profile: Dict[str, str]) -> None:
        """Save user profile to disk."""
        with self._lock:
            try:
                with self._path.open("w", encoding="utf-8") as handle:
                    json.dump(profile, handle, indent=2)
            except Exception as exc:
                logger.error(
                    "user profile save failed",
                    extra={"error": str(exc), "path": str(self._path)},
                )
                raise

    def load(self) -> Dict[str, str]:
        """Load user profile from disk."""
        with self._lock:
            try:
                if not self._path.exists():
                    return {}
                with self._path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
            except Exception as exc:
                logger.error(
                    "user profile load failed",
                    extra={"error": str(exc), "path": str(self._path)},
                )
                return {}

    def get_field(self, key: str) -> Optional[str]:
        """Get a single field from the profile."""
        profile = self.load()
        return profile.get(key)

    def update_field(self, key: str, value: str) -> None:
        """Update a single field in the profile."""
        profile = self.load()
        profile[key] = value
        self.save(profile)

    def clear(self) -> None:
        """Clear the profile."""
        with self._lock:
            try:
                if self._path.exists():
                    self._path.unlink()
            except Exception as exc:
                logger.warning(
                    "user profile clear failed", extra={"error": str(exc), "path": str(self._path)}
                )


_user_profile = UserProfile(_PROFILE_PATH)


def get_user_profile() -> UserProfile:
    return _user_profile


__all__ = ["UserProfile", "get_user_profile"]
