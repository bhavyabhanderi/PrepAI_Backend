from fastapi import APIRouter, Depends, status
from typing import Any
from app.models.user import Profile, User
from app.schemas.user import ProfileUpdate
from app.services.profile_service import ProfileService
from app.auth.dependencies import get_current_user

router = APIRouter()

@router.get("/me", response_model=Profile)
async def get_my_profile(current_user: User = Depends(get_current_user)) -> Any:
    """
    Get the current user's profile.
    """
    profile = await ProfileService.get_profile(str(current_user.id))
    return profile

@router.put("/me", response_model=Profile)
async def update_my_profile(
    profile_update: ProfileUpdate, 
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update the current user's profile.
    """
    profile = await ProfileService.update_profile(str(current_user.id), profile_update)
    return profile
