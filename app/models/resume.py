from typing import Optional, List, Dict, Any
from datetime import datetime
from beanie import Document
from pydantic import Field

class Resume(Document):
    user_id: str
    file_name: str
    file_path: str
    content_type: str
    version: int = 1
    parsed_text: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "resumes"

class ResumeAnalysis(Document):
    resume_id: str
    user_id: str
    ats_score: int = 0
    grammar_score: int = 0
    formatting_score: int = 0
    missing_skills: List[str] = []
    recommended_skills: List[str] = []
    resume_summary: Optional[str] = None
    improvement_suggestions: List[str] = []
    raw_ai_response: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "resume_analysis"
