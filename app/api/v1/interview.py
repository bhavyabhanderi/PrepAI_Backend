from fastapi import APIRouter, Depends, status
from typing import Any, List
from app.models.user import User
from app.models.interview import Interview
from app.models.analytics import PerformanceReport
from app.schemas.interview import InterviewCreate, InterviewResponse, QuestionResponse, AnswerSubmit, AnswerResponse
from app.services.interview_service import InterviewService
from app.auth.dependencies import get_current_user

router = APIRouter()
interview_service = InterviewService()

@router.get("/history")
async def get_interview_history(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get all interviews for the current user, sorted by creation date (newest first).
    """
    interviews = await Interview.find(
        Interview.user_id == str(current_user.id)
    ).sort(-Interview.created_at).to_list()

    # Scores live in the PerformanceReport collection (keyed by interview_id),
    # not on the Interview itself. Fetch them once and map by interview_id so
    # the history can show the overall score instead of "N/A".
    reports = await PerformanceReport.find(
        PerformanceReport.user_id == str(current_user.id)
    ).to_list()
    score_by_interview = {r.interview_id: r.overall_score for r in reports}

    result = []
    for iv in interviews:
        result.append({
            "id": str(iv.id),
            "type": iv.type.value,
            "status": iv.status.value,
            "job_role": iv.job_role,
            "difficulty_level": iv.difficulty_level,
            "created_at": iv.created_at.isoformat() if iv.created_at else None,
            "completed_at": iv.completed_at.isoformat() if iv.completed_at else None,
            "score": score_by_interview.get(str(iv.id)),
        })
    return result


@router.post("/", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def create_interview(
    data: InterviewCreate,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Start a new interview session and generate questions.
    """
    interview = await interview_service.create_interview(str(current_user.id), data)
    return interview

@router.get("/{interview_id}/next", response_model=QuestionResponse)
async def get_next_question(
    interview_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get the next unanswered question for an active interview.
    """
    question = await interview_service.get_next_question(interview_id)
    return question

@router.post("/{interview_id}/answer", response_model=AnswerResponse)
async def submit_answer(
    interview_id: str,
    data: AnswerSubmit,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Submit an answer, evaluate it via AI, and return score & feedback.
    """
    answer = await interview_service.submit_answer(str(current_user.id), interview_id, data)
    return answer

from pydantic import BaseModel
class AptitudeSubmitRequest(BaseModel):
    answers: List[dict]

@router.get("/{interview_id}/aptitude", response_model=List[QuestionResponse])
async def get_aptitude_questions(
    interview_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get all questions for an aptitude test, omitting correct answers.
    """
    from app.models.interview import Question
    questions = await Question.find(Question.interview_id == interview_id).sort("order_index").to_list()
    # Omit correct_answer before sending to client
    for q in questions:
        q.correct_answer = None
    return questions

@router.post("/{interview_id}/aptitude/submit")
async def submit_aptitude_test(
    interview_id: str,
    data: AptitudeSubmitRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Submit all answers for an aptitude test and get the final score.
    """
    result = await interview_service.submit_aptitude_test(str(current_user.id), interview_id, data.answers)
    return result
