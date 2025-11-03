"""User profile routes."""

from fastapi import APIRouter
from pydantic import BaseModel

from ..services.user_profile import get_user_profile

router = APIRouter(prefix="/profile", tags=["profile"])


class UserProfileData(BaseModel):
    """User profile data."""
    userName: str = ""
    birthDate: str = ""
    location: str = ""


@router.post("/save")
def save_profile(profile: UserProfileData):
    """Save user profile."""
    profile_store = get_user_profile()
    profile_dict = {
        "userName": profile.userName,
        "birthDate": profile.birthDate,
        "location": profile.location,
    }
    profile_store.save(profile_dict)
    return {"ok": True}


@router.get("/load")
def load_profile():
    """Load user profile."""
    profile_store = get_user_profile()
    profile_data = profile_store.load()
    return {
        "ok": True,
        "profile": {
            "userName": profile_data.get("userName", ""),
            "birthDate": profile_data.get("birthDate", ""),
            "location": profile_data.get("location", ""),
        }
    }
