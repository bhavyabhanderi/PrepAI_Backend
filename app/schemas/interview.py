from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, List, Annotated
from datetime import datetime
from app.models.interview import InterviewType, InterviewStatus

# Custom type to handle MongoDB ObjectId serialization in Pydantic v2 schemas
PyObjectId = Annotated[str, BeforeValidator(str)]

class InterviewCreate(BaseModel):
    type: InterviewType
    company: Optional[str] = None
    job_role: Optional[str] = None
    difficulty_level: str = "medium"
    job_description: Optional[str] = None

class InterviewResponse(BaseModel):
    id: PyObjectId
    user_id: PyObjectId
    type: InterviewType
    status: InterviewStatus
    company: Optional[str]
    job_role: Optional[str]
    difficulty_level: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class QuestionResponse(BaseModel):
    id: PyObjectId
    interview_id: PyObjectId
    question_text: str
    order_index: int
    difficulty: str
    options: Optional[List[str]] = None
    
    
    class Config:
        from_attributes = True

class AnswerSubmit(BaseModel):
    question_id: PyObjectId
    answer_text: str
    
class AnswerResponse(BaseModel):
    id: PyObjectId
    question_id: PyObjectId
    answer_text: str
    score: Optional[int]
    feedback: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
