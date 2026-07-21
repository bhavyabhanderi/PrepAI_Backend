from fastapi import HTTPException, status
from app.models.user import Profile
from app.schemas.user import ProfileUpdate
from typing import Optional

class ProfileService:
    @staticmethod
    async def get_profile(user_id: str) -> Optional[Profile]:
        profile = await Profile.find_one(Profile.user_id == user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        return profile

    @staticmethod
    async def update_profile(user_id: str, profile_update: ProfileUpdate) -> Profile:
        profile = await Profile.find_one(Profile.user_id == user_id)
        if not profile:
            # Create a new profile if it somehow doesn't exist
            profile = Profile(user_id=user_id)
            await profile.insert()
            
        # Update fields dynamically
        update_data = profile_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)
            
        import datetime
        profile.updated_at = datetime.datetime.utcnow()
        await profile.save()
        return profile
