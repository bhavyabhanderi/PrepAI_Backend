from fastapi import HTTPException, status
from app.models.coding import CodingSubmission
from app.schemas.coding import CodeExecutionRequest
from app.ai.code_reviewer import CodeReviewer
import asyncio

class CodingService:
    def __init__(self):
        self.reviewer = CodeReviewer()

    async def execute_and_review_code(self, user_id: str, data: CodeExecutionRequest) -> CodingSubmission:
        """
        Execute code safely (mocked here for simplicity, in prod use Judge0 or isolated Docker)
        and perform AI review for complexities.
        """
        # Validate if code is empty or unchanged from the template
        code_stripped = data.source_code.strip() if data.source_code else ""
        is_invalid = (
            not code_stripped
            or (code_stripped.endswith("pass") and "def solution" in code_stripped and "return" not in code_stripped)
            or (code_stripped.endswith("}") and "function solution" in code_stripped and "return" not in code_stripped)
        )
        
        if is_invalid:
            submission = CodingSubmission(
                user_id=user_id,
                interview_id=data.interview_id,
                language=data.language,
                source_code=data.source_code or "",
                test_cases_passed=0,
                total_test_cases=len(data.test_cases) if data.test_cases else 1,
                status="failed",
                error_message="Compilation/Validation Error: Please write a valid solution before running or submitting.",
                time_complexity="N/A",
                space_complexity="N/A",
                optimization_suggestions=["Please write a complete solution to solve the problem."],
                code_quality_score=0
            )
            await submission.insert()
            return submission

        # 1. Mock Code Execution
        # In a real environment, you'd send `data.source_code` to a sandboxed environment
        # and run `data.test_cases` against it.
        await asyncio.sleep(0.5) # Simulate execution delay
        
        # We will mock the execution passing all test cases for demonstration
        total_tests = len(data.test_cases) if data.test_cases else 1
        passed_tests = total_tests
        
        # 2. AI Code Review
        review = await self.reviewer.analyze_code(data.source_code, data.language)
        
        # 3. Save Submission
        submission = CodingSubmission(
            user_id=user_id,
            interview_id=data.interview_id,
            language=data.language,
            source_code=data.source_code,
            test_cases_passed=passed_tests,
            total_test_cases=total_tests,
            execution_time_ms=12.5, # Mock metric
            memory_used_kb=1024.0, # Mock metric
            status="passed" if passed_tests == total_tests else "failed",
            time_complexity=review.get("time_complexity"),
            space_complexity=review.get("space_complexity"),
            optimization_suggestions=review.get("optimization_suggestions", []),
            code_quality_score=review.get("code_quality_score", 0)
        )
        await submission.insert()
        return submission
