from typing import Optional, List, Dict, Any
from datetime import datetime
from beanie import Document
from pydantic import Field

class PerformanceReport(Document):
    user_id: str
    interview_id: str
    overall_score: float = 0.0
    communication_score: float = 0.0
    technical_score: float = 0.0
    coding_score: float = 0.0
    confidence_score: float = 0.0
    grammar_score: float = 0.0
    time_management_score: float = 0.0
    strengths: List[str] = []
    weaknesses: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "performance_reports"

class LearningPlan(Document):
    user_id: str
    report_id: Optional[str] = None
    recommended_topics: List[str] = []
    practice_questions: List[Dict[str, str]] = [] # e.g. [{"topic": "Arrays", "link": "leetcode.com/..."}]
    youtube_resources: List[Dict[str, str]] = []
    project_ideas: List[str] = []
    weekly_schedule: Dict[str, List[Any]] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "learning_plans"

class UserProgress(Document):
    user_id: str
    interview_id: str
    overall_score: float
    communication_score: float
    technical_score: float
    coding_score: float
    confidence_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "user_progress"
