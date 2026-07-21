from pydantic import BaseModel, BeforeValidator
from typing import Optional, List, Dict, Any, Annotated
from datetime import datetime

# Custom type to handle MongoDB ObjectId serialization in Pydantic v2 schemas
PyObjectId = Annotated[str, BeforeValidator(str)]

class ResumeResponse(BaseModel):
    id: PyObjectId
    user_id: PyObjectId
    file_name: str
    version: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class ResumeAnalysisResponse(BaseModel):
    id: PyObjectId
    resume_id: PyObjectId
    ats_score: int
    grammar_score: int
    formatting_score: int
    missing_skills: List[str]
    recommended_skills: List[str]
    resume_summary: Optional[str]
    improvement_suggestions: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
