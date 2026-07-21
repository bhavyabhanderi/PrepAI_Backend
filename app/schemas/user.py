from pydantic import BaseModel, EmailStr, Field, BeforeValidator
from typing import Optional, List, Annotated
from datetime import datetime

# Custom type to handle MongoDB ObjectId serialization in Pydantic v2 schemas
PyObjectId = Annotated[str, BeforeValidator(str)]

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None

# --- User Auth Schemas ---
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleToken(BaseModel):
    token: str

class UserResponse(BaseModel):
    id: PyObjectId
    name: str
    email: EmailStr
    is_active: bool
    is_admin: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Profile Schemas ---
class ProfileUpdate(BaseModel):
    mobile: Optional[str] = None
    college: Optional[str] = None
    department: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[int] = None
    skills: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    experience: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    profile_image_url: Optional[str] = None
