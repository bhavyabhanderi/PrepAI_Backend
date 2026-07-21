from pydantic import BaseModel, BeforeValidator
from typing import Optional, List, Dict, Annotated, Any
from datetime import datetime

# Custom type to handle MongoDB ObjectId serialization in Pydantic v2 schemas
PyObjectId = Annotated[str, BeforeValidator(str)]

class PerformanceReportResponse(BaseModel):
    id: PyObjectId
    user_id: PyObjectId
    interview_id: PyObjectId
    overall_score: float
    communication_score: float
    technical_score: float
    coding_score: float
    confidence_score: float
    grammar_score: float
    time_management_score: float
    strengths: List[str]
    weaknesses: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class LearningPlanResponse(BaseModel):
    id: PyObjectId
    user_id: PyObjectId
    report_id: PyObjectId
    recommended_topics: List[str]
    practice_questions: List[Dict[str, str]]
    youtube_resources: List[Dict[str, str]]
    project_ideas: List[str]
    weekly_schedule: Dict[str, List[Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True
class UpdateTaskRequest(BaseModel):
    day: str
    task_index: int
    done: bool

class AdminDashboardStats(BaseModel):
    total_users: int
    total_interviews: int
    total_coding_submissions: int
    average_interview_score: float
