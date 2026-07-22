from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import Dict, Any, List
from app.ai.syllabus_analyzer import SyllabusAnalyzer
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.syllabus import SavedSyllabus
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

syllabus_analyzer = SyllabusAnalyzer()

class ChatRequest(BaseModel):
    topic: str
    message: str
    history: List[Dict[str, str]] = []

@router.post("/upload", response_model=SavedSyllabus)
async def upload_syllabus(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """
    Upload a syllabus PDF file, extract its text, analyze it using NLP, and save it to the database.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        # Extract text from the PDF
        syllabus_text = await syllabus_analyzer.parse_syllabus_file(file)
        
        if not syllabus_text:
            raise HTTPException(status_code=400, detail="Could not extract text from the PDF.")
            
        # Analyze the syllabus using Groq
        analysis_result = await syllabus_analyzer.analyze_syllabus(syllabus_text)
        
        # Save to DB
        saved_syllabus = SavedSyllabus(
            user_id=str(current_user.id),
            subject=analysis_result.get("subject", "Unknown Subject"),
            chapters=analysis_result.get("chapters", []),
            file_name=file.filename
        )
        await saved_syllabus.insert()
        
        return saved_syllabus
        
    except Exception as e:
        logger.error(f"Error in upload_syllabus endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[SavedSyllabus])
async def get_saved_syllabi(current_user: User = Depends(get_current_user)):
    """
    Get all saved syllabi for the current user.
    """
    syllabi = await SavedSyllabus.find({"user_id": str(current_user.id)}).sort("-created_at").to_list()
    return syllabi

@router.post("/chat")
async def chat_on_topic(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """
    Chat with an AI tutor on a specific topic.
    """
    try:
        response_text = await syllabus_analyzer.chat_on_topic(
            topic=request.topic,
            message=request.message,
            history=request.history
        )
        return {"response": response_text}
    except Exception as e:
        logger.error(f"Error in syllabus chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to chat with AI.")
