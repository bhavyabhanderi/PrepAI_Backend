import json
import logging
from groq import AsyncGroq
from app.config.config import settings

logger = logging.getLogger(__name__)

class CodeReviewer:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

    async def analyze_code(self, source_code: str, language: str) -> dict:
        """
        Analyze code using Groq to get Time/Space complexity and optimization suggestions.
        """
        if not self.client:
            return {
                "time_complexity": "O(N) (Dummy)",
                "space_complexity": "O(1) (Dummy)",
                "optimization_suggestions": ["Configure Groq API for real analysis."],
                "code_quality_score": 80
            }

        prompt = f"""
        You are an Expert Software Engineer reviewing the following {language} code.
        
        Code:
        ```
        {source_code}
        ```
        
        Analyze the code and respond with a JSON object containing:
        {{
            "time_complexity": "(string, e.g. O(N))",
            "space_complexity": "(string, e.g. O(1))",
            "optimization_suggestions": [(list of strings)],
            "code_quality_score": (integer 0-100)
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
            logger.error(f"Groq API Error in analyze_code: {e}")
            return {
                "time_complexity": "Unknown",
                "space_complexity": "Unknown",
                "optimization_suggestions": ["Error analyzing code."],
                "code_quality_score": 0
            }
