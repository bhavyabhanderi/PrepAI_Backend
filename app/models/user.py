from typing import Optional, List
from datetime import datetime
from beanie import Document
from pydantic import EmailStr, Field

class User(Document):
    name: str
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "users"

class Profile(Document):
    user_id: str # Reference to User document ID
    mobile: Optional[str] = None
    college: Optional[str] = None
    department: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[int] = None
    skills: List[str] = []
    languages: List[str] = []
    experience: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "profiles"

class Admin(Document):
    user_id: str
    permissions: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "admins"
