from typing import Any
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.user import UserResponse, UserCreate, Token
from app.services.auth_service import AuthService
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate) -> Any:
    """
    Register a new user.
    """
    user = await AuthService.register_user(user_in)
    return user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    # We map form_data.username to email since OAuth2PasswordRequestForm expects username
    from app.schemas.user import UserLogin
    user_login = UserLogin(email=form_data.username, password=form_data.password)
    
    result = await AuthService.authenticate(user_login)
    return {
        "access_token": result["access_token"],
        "token_type": result["token_type"]
    }

@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)) -> Any:
    """
    Get current user information.
    """
    return current_user

@router.post("/google", response_model=Token)
async def google_login(token_data: __import__('app.schemas.user', fromlist=['GoogleToken']).GoogleToken) -> Any:
    """
    Login or register via Google OAuth Token.
    """
    result = await AuthService.authenticate_google(token_data.token)
    return {
        "access_token": result["access_token"],
        "token_type": result["token_type"]
    }
