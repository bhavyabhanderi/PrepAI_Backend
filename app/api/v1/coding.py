from fastapi import APIRouter, Depends
from typing import Any, List
from app.models.user import User
from app.models.coding import CodingProblem
from app.auth.dependencies import get_current_user
from app.schemas.coding import CodeExecutionRequest, CodeExecutionResponse
from app.services.coding_service import CodingService

from app.ai.coding_generator import CodingGenerator
from app.ai.practice_generator import PracticeGenerator

router = APIRouter()
coding_service = CodingService()
coding_generator = CodingGenerator()
practice_generator = PracticeGenerator()

@router.get("/history")
async def get_coding_history(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get coding history for the user.
    """
    from app.models.coding import CodingSubmission
    submissions = await CodingSubmission.find(CodingSubmission.user_id == str(current_user.id)).sort(-CodingSubmission.created_at).to_list()
    return submissions

@router.get("/problems", response_model=List[CodingProblem])
async def get_coding_problems(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Generate and return a brand new dynamic coding problem.
    """
    new_problem = await coding_generator.generate_problem()
    return [new_problem]


@router.get("/sql-problems")
async def get_sql_problems(
    difficulty: str = "medium",
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Generate and return a dynamic SQL practice problem.
    """
    new_problem = await practice_generator.generate_sql_problem(difficulty=difficulty)
    return [new_problem]


@router.get("/debugging-problems")
async def get_debugging_problems(
    difficulty: str = "medium",
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Generate and return a dynamic Debugging practice problem.
    """
    new_problem = await practice_generator.generate_debugging_problem(difficulty=difficulty)
    return [new_problem]


@router.post("/execute", response_model=CodeExecutionResponse)
async def execute_and_review_code(
    data: CodeExecutionRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Execute source code against test cases and perform AI review for time/space complexity.
    """
    submission = await coding_service.execute_and_review_code(str(current_user.id), data)
    return submission
