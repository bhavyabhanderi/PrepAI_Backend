from pydantic import BaseModel
from typing import Optional, List

class VoiceAnalysisResponse(BaseModel):
    transcription: str
    speaking_speed_wpm: float
    words_per_minute: float
    confidence_score: int
    filler_words_detected: List[str]
    pause_detected_count: int
    feedback: Optional[str]

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "default"

class VoiceFirstQuestionRequest(BaseModel):
    job_role: str
    job_description: Optional[str] = None

class VoiceChatRequest(BaseModel):
    job_role: str
    job_description: Optional[str] = None
    transcription: str
    history: List[dict] = []
