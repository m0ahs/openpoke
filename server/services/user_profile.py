"""User profile storage and retrieval - using centralized DataManager."""

from typing import Dict, Optional

from .data_manager import get_data_manager

PROFILE_FILENAME = "user_profile.json"


class UserProfile:
    """
    User profile storage using Railway Volume DataManager.

    Features:
    - Automatic backups before changes
    - Atomic writes (no corruption)
    - Thread-safe operations
    - Automatic validation
    """

    def __init__(self):
        self._data_manager = get_data_manager()

    def save(self, profile: Dict[str, str]) -> None:
        """
        Save user profile to disk with automatic backup.

        Args:
            profile: Dictionary containing user profile data
        """
        self._data_manager.save_json(PROFILE_FILENAME, profile, backup=True)

    def load(self) -> Dict[str, str]:
        """
        Load user profile from disk.

        Returns:
            Dictionary with profile data, or empty dict if not found
        """
        return self._data_manager.load_json(PROFILE_FILENAME)

    def get_field(self, key: str) -> Optional[str]:
        """
        Get a single field from the profile.

        Args:
            key: Field name to retrieve

        Returns:
            Field value or None if not found
        """
        profile = self.load()
        return profile.get(key)

    def update_field(self, key: str, value: str) -> None:
        """
        Update a single field in the profile.

        Args:
            key: Field name to update
            value: New value
        """
        self._data_manager.update_field(PROFILE_FILENAME, key, value, backup=True)

    def clear(self) -> None:
        """Clear the profile (with automatic backup)."""
        self._data_manager.delete_file(PROFILE_FILENAME, backup=True)

    def restore_from_backup(self) -> bool:
        """
        Restore profile from most recent backup.

        Returns:
            True if successful, False if no backup exists
        """
        return self._data_manager.restore_from_backup(PROFILE_FILENAME)


# Singleton instance
_user_profile: Optional[UserProfile] = None


def get_user_profile() -> UserProfile:
    """Get the singleton UserProfile instance."""
    global _user_profile
    if _user_profile is None:
        _user_profile = UserProfile()
    return _user_profile


__all__ = ["UserProfile", "get_user_profile"]
