from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from fastapi.responses import Response
from typing import Any
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.ai.voice_service import VoiceService
from app.schemas.voice import VoiceAnalysisResponse, TTSRequest, VoiceFirstQuestionRequest, VoiceChatRequest

router = APIRouter()
voice_service = VoiceService()

@router.post("/stt", response_model=VoiceAnalysisResponse)
async def process_speech_to_text(
    audio_file: UploadFile = File(...),
    duration_sec: float = Form(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Process an audio file through Nvidia STT, analyze speech features, and return transcription.
    """
    audio_bytes = await audio_file.read()
    
    # 1. Transcribe Audio
    transcription = await voice_service.speech_to_text(audio_bytes, audio_file.filename)
    
    # 2. Analyze Features
    analysis = voice_service.analyze_voice_features(transcription, duration_sec)
    
    return analysis

@router.post("/tts")
async def process_text_to_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Convert text to speech using Nvidia TTS API and return the audio file stream.
    """
    audio_bytes = await voice_service.text_to_speech(request.text)
    
    # If API fails or key is missing, it might return empty bytes
    if not audio_bytes:
        return Response(content="TTS failed", status_code=500)
        
    return Response(content=audio_bytes, media_type="audio/mpeg")

@router.post("/first-question")
async def get_voice_first_question(
    request: VoiceFirstQuestionRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get the initial greeting and first question for the voice interview.
    """
    question_text = await voice_service.voice_chat_first_question(
        job_role=request.job_role,
        job_description=request.job_description
    )
    return {"text": question_text}

@router.post("/chat")
async def process_voice_chat(
    request: VoiceChatRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get the next question and reply dynamically during the voice interview.
    """
    reply_text = await voice_service.voice_chat(
        job_role=request.job_role,
        job_description=request.job_description,
        transcription=request.transcription,
        history=request.history
    )
    return {"text": reply_text}
