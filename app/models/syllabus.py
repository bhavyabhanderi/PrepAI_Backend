from typing import List, Dict, Any
from datetime import datetime
from beanie import Document
from pydantic import Field

class SavedSyllabus(Document):
    user_id: str
    subject: str
    chapters: List[Dict[str, Any]] = []
    file_name: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "saved_syllabi"
