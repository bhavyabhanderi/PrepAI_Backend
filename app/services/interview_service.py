from fastapi import HTTPException, status
from app.models.interview import Interview, Question, Answer, InterviewStatus, InterviewType
from app.schemas.interview import InterviewCreate, AnswerSubmit
from app.models.resume import Resume
from app.ai.interview_generator import InterviewGenerator
from datetime import datetime

class InterviewService:
    def __init__(self):
        self.generator = InterviewGenerator()

    async def create_interview(self, user_id: str, data: InterviewCreate) -> Interview:
        # Check active resume if resume-based context is needed
        active_resume = await Resume.find_one(Resume.user_id == user_id, Resume.is_active == True)
        resume_id = str(active_resume.id) if active_resume else None
        resume_text = active_resume.parsed_text if active_resume else None
        
        # Create Interview record
        interview = Interview(
            user_id=user_id,
            type=data.type,
            company=data.company,
            job_role=data.job_role or "Software Engineer",
            difficulty_level=data.difficulty_level,
            job_description=data.job_description,
            resume_id=resume_id
        )
        await interview.insert()
        
        # Generate Initial Questions
        if data.type == InterviewType.APTITUDE:
            q_data = await self.generator.generate_aptitude_questions(
                difficulty=interview.difficulty_level or "all",
                count=20
            )
        else:
            q_data = await self.generator.generate_questions(
                interview_type=data.type.value,
                job_role=interview.job_role,
                difficulty=interview.difficulty_level,
                count=5,
                resume_text=resume_text,
                job_description=interview.job_description
            )
        
        # Save Questions
        for idx, q in enumerate(q_data):
            question = Question(
                interview_id=str(interview.id),
                question_text=q.get("question_text", "Could not generate question"),
                order_index=idx + 1,
                difficulty=q.get("difficulty", "medium"),
                expected_keywords=q.get("expected_keywords", []),
                options=q.get("options"),
                correct_answer=q.get("correct_answer")
            )
            await question.insert()
            
        return interview

    async def get_next_question(self, interview_id: str) -> Question:
        interview = await Interview.get(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
            
        if interview.status == InterviewStatus.SCHEDULED:
            interview.status = InterviewStatus.IN_PROGRESS
            interview.started_at = datetime.utcnow()
            await interview.save()
            
        # Find questions for this interview
        questions = await Question.find(Question.interview_id == interview_id).sort("order_index").to_list()
        
        # Find answered questions
        answers = await Answer.find(Answer.interview_id == interview_id).to_list()
        answered_q_ids = [a.question_id for a in answers]
        
        # Return first unanswered question
        for q in questions:
            if str(q.id) not in answered_q_ids:
                return q
                
        # If all answered, mark completed
        if interview.status != InterviewStatus.COMPLETED:
            interview.status = InterviewStatus.COMPLETED
            interview.completed_at = datetime.utcnow()
            await interview.save()
            
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interview is already completed.")

    async def submit_answer(self, user_id: str, interview_id: str, data: AnswerSubmit) -> Answer:
        question = await Question.get(data.question_id)
        if not question or question.interview_id != interview_id:
            raise HTTPException(status_code=404, detail="Question not found")
            
        # Check if already answered
        existing = await Answer.find_one(Answer.question_id == data.question_id)
        if existing:
            raise HTTPException(status_code=400, detail="Question already answered")
            
        # Evaluate Answer
        eval_result = await self.generator.evaluate_answer(
            question_text=question.question_text,
            answer_text=data.answer_text,
            expected_keywords=question.expected_keywords
        )
        
        # Save Answer
        answer = Answer(
            interview_id=interview_id,
            question_id=data.question_id,
            user_id=user_id,
            answer_text=data.answer_text,
            score=eval_result.get("score"),
            feedback=eval_result.get("feedback")
        )
        await answer.insert()
        return answer

    async def submit_aptitude_test(self, user_id: str, interview_id: str, answers: list) -> dict:
        interview = await Interview.get(interview_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
            
        if interview.status == InterviewStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Interview is already completed")
            
        questions = await Question.find(Question.interview_id == interview_id).to_list()
        q_dict = {str(q.id): q for q in questions}
        
        total_score = 0
        max_score = len(questions) * 10
        
        for ans in answers:
            q_id = ans.get("question_id")
            answer_text = ans.get("answer_text")
            
            question = q_dict.get(q_id)
            if not question:
                continue
                
            is_correct = False
            if question.correct_answer and answer_text:
                is_correct = str(question.correct_answer).strip().lower() == str(answer_text).strip().lower()
                
            score = 10 if is_correct else 0
            total_score += score
            
            answer_record = Answer(
                interview_id=interview_id,
                question_id=q_id,
                user_id=user_id,
                answer_text=answer_text or "",
                score=score,
                feedback="Correct" if is_correct else f"Incorrect. Correct answer is: {question.correct_answer}"
            )
            await answer_record.insert()
            
        interview.status = InterviewStatus.COMPLETED
        interview.completed_at = datetime.utcnow()
        await interview.save()
        
        correct_count = total_score // 10
        total_questions = len(questions)
        percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        return {
            "score": percentage,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "message": "Aptitude test submitted successfully"
        }
