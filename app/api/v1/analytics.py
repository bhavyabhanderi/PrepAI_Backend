from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from typing import Any
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.schemas.analytics import PerformanceReportResponse, LearningPlanResponse, UpdateTaskRequest
from app.models.analytics import LearningPlan
from app.services.analytics_service import AnalyticsService
from fastapi import HTTPException

router = APIRouter()
analytics_service = AnalyticsService()

@router.post("/report/{interview_id}", response_model=PerformanceReportResponse)
async def generate_report(
    interview_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Generate a performance report summarizing the completed interview.
    """
    report = await analytics_service.generate_performance_report(str(current_user.id), interview_id)
    return report

@router.post("/learning-plan/resume", response_model=LearningPlanResponse)
async def generate_learning_plan_from_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Generate a learning plan from a resume upload.
    """
    plan = await analytics_service.generate_learning_plan_from_resume(str(current_user.id), file)
    return plan

@router.post("/skills-test")
async def generate_skills_test(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Parse resume and generate a 10-question MCQ skills assessment test.
    """
    result = await analytics_service.generate_skills_test(file)
    return result

@router.post("/learning-plan/resume-with-score", response_model=LearningPlanResponse)
async def generate_learning_plan_with_score(
    file: UploadFile = File(...),
    quiz_score: int = 0,
    weak_topics: str = "",
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Generate a personalized learning plan using resume + quiz score results.
    """
    weak_list = [t.strip() for t in weak_topics.split(",") if t.strip()]
    plan = await analytics_service.generate_learning_plan_from_resume_with_score(
        str(current_user.id), file, quiz_score, weak_list
    )
    return plan


@router.post("/learning-plan/{report_id}", response_model=LearningPlanResponse)
async def generate_learning_plan(
    report_id: str,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Generate an AI-driven personalized learning plan based on the performance report.
    """
    plan = await analytics_service.generate_learning_plan(str(current_user.id), report_id)
    return plan

@router.get("/learning-plan", response_model=LearningPlanResponse)
async def get_latest_learning_plan(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get the user's most recent learning plan.
    """
    plan = await LearningPlan.find(
        LearningPlan.user_id == str(current_user.id)
    ).sort(-LearningPlan.created_at).first_or_none()
    
    if not plan:
        raise HTTPException(status_code=404, detail="No learning plan found")
    return plan

@router.put("/learning-plan/{plan_id}/task")
async def update_learning_plan_task(
    plan_id: str,
    payload: UpdateTaskRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update a specific task's done status in the learning plan.
    """
    plan = await LearningPlan.get(plan_id)
    if not plan or plan.user_id != str(current_user.id):
        raise HTTPException(status_code=404, detail="Learning plan not found")
        
    day = payload.day
    if day not in plan.weekly_schedule:
        raise HTTPException(status_code=400, detail="Invalid day")
        
    tasks = plan.weekly_schedule[day]
    if payload.task_index < 0 or payload.task_index >= len(tasks):
        raise HTTPException(status_code=400, detail="Invalid task index")
        
    tasks[payload.task_index]["done"] = payload.done
    await plan.save()
    return {"message": "Task updated successfully"}

@router.get("/dashboard")
async def get_dashboard(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get aggregated user dashboard metrics.
    """
    return await analytics_service.get_dashboard_data(str(current_user.id))

@router.get("/performance-kpis")
async def get_performance_kpis(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get aggregated performance metrics for charts.
    """
    return await analytics_service.get_performance_kpis(str(current_user.id))

