from typing import Optional
from datetime import datetime
from beanie import Document
from pydantic import Field

class Rating(Document):
    user_id: str
    rating_value: int = Field(ge=1, le=5)
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "ratings"
