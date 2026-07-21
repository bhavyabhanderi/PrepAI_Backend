from fastapi import APIRouter, Depends, UploadFile, File, status
from typing import Any
from app.models.user import User
from app.schemas.resume import ResumeAnalysisResponse
from app.services.resume_service import ResumeService
from app.auth.dependencies import get_current_user

router = APIRouter()
resume_service = ResumeService()

@router.post("/upload", response_model=ResumeAnalysisResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Upload a resume (PDF/DOCX), parse it, and perform AI analysis.
    """
    analysis = await resume_service.upload_and_process_resume(str(current_user.id), file)
    return analysis

@router.get("/analysis", response_model=ResumeAnalysisResponse)
async def get_resume_analysis(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get the AI analysis of the current active resume.
    """
    analysis = await resume_service.get_latest_resume_analysis(str(current_user.id))
    return analysis
