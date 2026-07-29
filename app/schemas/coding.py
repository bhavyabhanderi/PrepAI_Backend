from pydantic import BaseModel, BeforeValidator
from typing import Optional, List, Annotated
from datetime import datetime

# Custom type to handle MongoDB ObjectId serialization in Pydantic v2 schemas
PyObjectId = Annotated[str, BeforeValidator(str)]

class CodeExecutionRequest(BaseModel):
    interview_id: Optional[str] = None
    language: str
    source_code: str
    stdin: Optional[str] = None
    test_cases: List[dict] = [] # e.g. [{"input": "1 2", "expected_output": "3"}]

class CodeExecutionResponse(BaseModel):
    id: PyObjectId
    status: str
    test_cases_passed: int
    total_test_cases: int
    execution_time_ms: float
    memory_used_kb: float
    output: Optional[str] = None
    error_message: Optional[str]
    time_complexity: Optional[str]
    space_complexity: Optional[str]
    optimization_suggestions: List[str]
    code_quality_score: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True
