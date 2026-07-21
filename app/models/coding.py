from typing import Optional, List
from datetime import datetime
from beanie import Document
from pydantic import Field

class CodingSubmission(Document):
    user_id: str
    interview_id: Optional[str] = None
    language: str
    source_code: str
    test_cases_passed: int = 0
    total_test_cases: int = 0
    execution_time_ms: float = 0.0
    memory_used_kb: float = 0.0
    status: str = "pending" # pending, passed, failed, error
    error_message: Optional[str] = None
    
    # AI Review Data
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    optimization_suggestions: List[str] = []
    code_quality_score: Optional[int] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "coding_submissions"

class CodingProblem(Document):
    title: str
    difficulty: str
    description: str
    examples: List[dict] = []
    constraints: List[str] = []
    initial_templates: dict = {} # e.g. {"javascript": "...", "python": "..."}
    test_cases: List[dict] = [] # e.g. [{"input": "...", "expected_output": "..."}]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "coding_problems"
