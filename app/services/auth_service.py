from fastapi import HTTPException, status
from app.models.user import User, Profile
from app.schemas.user import UserCreate, UserLogin
from app.auth.security import get_password_hash, verify_password, create_access_token
from google.oauth2 import id_token
from google.auth.transport import requests
from app.config.config import settings
import secrets
import logging

logger = logging.getLogger(__name__)

class AuthService:
    
    @staticmethod
    async def register_user(user_in: UserCreate) -> User:
        # Check if user already exists
        existing_user = await User.find_one(User.email == user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email already exists in the system."
            )
            
        # Create new user
        hashed_password = get_password_hash(user_in.password)
        new_user = User(
            name=user_in.name,
            email=user_in.email,
            hashed_password=hashed_password
        )
        await new_user.insert()
        
        # Create an empty profile for the user
        new_profile = Profile(user_id=str(new_user.id))
        await new_profile.insert()
        
        return new_user

    @staticmethod
    async def authenticate(user_in: UserLogin):
        user = await User.find_one(User.email == user_in.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        if not verify_password(user_in.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
            
        # Create access token
        access_token = create_access_token(subject=str(user.id))
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }

    @staticmethod
    async def authenticate_google(token: str) -> dict:
        try:
            # The frontend is sending an OAuth Access Token, not an ID Token.
            # We verify it by fetching the user's profile info from Google.
            import urllib.request
            import json
            
            url = f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}"
            req = urllib.request.Request(url)
            try:
                with urllib.request.urlopen(req) as response:
                    idinfo = json.loads(response.read().decode())
            except Exception as exc:
                raise ValueError(f"Failed to fetch user info from Google: {exc}")
            
            email = idinfo.get('email')
            name = idinfo.get('name')
            
            if not email:
                raise ValueError("Email not found in Google token")
                
            # Check if user exists
            user = await User.find_one(User.email == email)
            
            if not user:
                # Create a new user automatically
                # Generate a random password since they login via Google
                random_password = secrets.token_urlsafe(16)
                hashed_password = get_password_hash(random_password)
                
                user = User(
                    name=name or email.split('@')[0],
                    email=email,
                    hashed_password=hashed_password,
                    is_active=True
                )
                await user.insert()
                
                # Create profile
                new_profile = Profile(user_id=str(user.id))
                await new_profile.insert()
                
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user"
                )
                
            # Create access token
            access_token = create_access_token(subject=str(user.id))
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user
            }
        except ValueError as e:
            logger.error(f"Google token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google token: {str(e)}"
            )
