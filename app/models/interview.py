from typing import Optional, List
from datetime import datetime
from beanie import Document
from pydantic import Field
from enum import Enum

class InterviewType(str, Enum):
    HR = "hr"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    COMPANY_SPECIFIC = "company_specific"
    APTITUDE = "aptitude"

class InterviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Interview(Document):
    user_id: str
    type: InterviewType
    status: InterviewStatus = InterviewStatus.SCHEDULED
    company: Optional[str] = None
    job_role: Optional[str] = None
    difficulty_level: str = "medium"  # beginner, medium, advanced
    resume_id: Optional[str] = None  # Reference to Resume
    job_description: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "interviews"

class Question(Document):
    interview_id: str
    question_text: str
    question_type: str = "dynamic" # fixed, dynamic, follow_up
    order_index: int
    difficulty: str
    expected_keywords: List[str] = []
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "questions"

class Answer(Document):
    interview_id: str
    question_id: str
    user_id: str
    answer_text: str
    audio_url: Optional[str] = None
    score: Optional[int] = None
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "answers"
