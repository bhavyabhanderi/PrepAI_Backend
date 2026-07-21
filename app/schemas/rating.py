from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class RatingCreate(BaseModel):
    rating_value: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    feedback: Optional[str] = Field(None, description="Optional feedback text")

class RatingResponse(BaseModel):
    id: str
    user_id: str
    rating_value: int
    feedback: Optional[str]
    created_at: datetime
    
class RatingStats(BaseModel):
    average_rating: float
    total_ratings: int
    total_users: int = 0
    total_interviews: int = 0
    success_rate: float = 0.0

class TestimonialResponse(BaseModel):
    name: str
    role: str
    text: str
    rating: int
