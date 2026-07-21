import json
import logging
from groq import AsyncGroq
from app.config.config import settings

logger = logging.getLogger(__name__)

class InterviewGenerator:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

    async def generate_questions(self, interview_type: str, job_role: str, difficulty: str, count: int = 5, resume_text: str = None, job_description: str = None) -> list:
        """
        Generate a list of interview questions based on the parameters.
        """
        if not self.client:
            logger.warning("Groq API key not configured. Returning dummy questions.")
            return self._get_dummy_questions(count)

        context = f"Job Role: {job_role}\nInterview Type: {interview_type}\nDifficulty: {difficulty}\n"
        if job_description:
            context += f"Job Description:\n{job_description}\n"
        if resume_text:
            context += f"Candidate Resume:\n{resume_text}\n"

        prompt = f"""
        You are an expert technical interviewer.
        Based on the following context, generate exactly {count} highly unique, diverse, and completely randomized interview questions.
        Ensure that these questions vary drastically on repeated runs so the candidate never sees the exact same questions twice!
        
        {context}
        
        Respond with a valid JSON array of objects. Each object MUST have this exact structure:
        {{
            "question_text": "(string)",
            "difficulty": "{difficulty}",
            "expected_keywords": ["keyword1", "keyword2"]
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                response_format={"type": "json_object"},
                temperature=0.9,
            )
            # The model might return {"questions": [...]}, we need to extract it
            content = json.loads(response.choices[0].message.content)
            if "questions" in content:
                return content["questions"]
            elif isinstance(content, list):
                return content
            else:
                # Attempt to find list values
                for v in content.values():
                    if isinstance(v, list):
                        return v
                return []
        except Exception as e:
            logger.error(f"Groq API Error in generate_questions: {e}")
            return self._get_dummy_questions(count)

    async def generate_aptitude_questions(self, count: int = 20) -> list:
        """
        Generate a list of aptitude multiple-choice questions.
        """
        if not self.client:
            logger.warning("Groq API key not configured. Returning dummy aptitude questions.")
            return self._get_dummy_aptitude_questions(count)

        prompt = f"""
        Generate exactly {count} aptitude test multiple-choice questions. 
        Include a mix of Mathematics, Logical Reasoning, and basic Coding/Computer Science questions.
        Ensure they are randomized and different every time.
        
        Respond with a valid JSON array of objects. Each object MUST have this exact structure:
        {{
            "questions": [
                {{
                    "question_text": "(string)",
                    "difficulty": "medium",
                    "options": ["option A", "option B", "option C", "option D"],
                    "correct_answer": "(string, must perfectly match one of the options)",
                    "expected_keywords": []
                }}
            ]
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                response_format={"type": "json_object"},
                temperature=0.9, # Higher temperature for variety
            )
            content = json.loads(response.choices[0].message.content)
            if "questions" in content:
                return content["questions"]
            elif isinstance(content, list):
                return content
            else:
                for v in content.values():
                    if isinstance(v, list):
                        return v
                return []
        except Exception as e:
            logger.error(f"Groq API Error in generate_aptitude_questions: {e}")
            return self._get_dummy_aptitude_questions(count)
            
    async def evaluate_answer(self, question_text: str, answer_text: str, expected_keywords: list) -> dict:
        """
        Evaluate an answer and return a score and feedback.
        """
        if not self.client:
            return {"score": 70, "feedback": "Dummy feedback since Groq is not configured."}
            
        prompt = f"""
        You are an expert interviewer. Evaluate the candidate's answer to the following question.
        
        Question: {question_text}
        Expected Keywords/Concepts: {', '.join(expected_keywords)}
        Candidate's Answer: {answer_text}
        
        Provide a JSON response with:
        {{
            "score": (integer 0-100),
            "feedback": "(string, constructive feedback and what could be improved)"
        }}
        """
        
        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Groq API Error in evaluate_answer: {e}")
            return {"score": 0, "feedback": "Error evaluating answer."}

    def _get_dummy_questions(self, count: int) -> list:
        return [
            {
                "question_text": f"Dummy question {i+1}?",
                "difficulty": "medium",
                "expected_keywords": ["dummy", "test"]
            }
            for i in range(count)
        ]

    def _get_dummy_aptitude_questions(self, count: int) -> list:
        return [
            {
                "question_text": f"Dummy aptitude question {i+1}?",
                "difficulty": "medium",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "expected_keywords": []
            }
            for i in range(count)
        ]
