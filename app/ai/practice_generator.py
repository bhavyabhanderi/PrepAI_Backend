import json
import random
import logging
from groq import AsyncGroq
from app.config.config import settings

logger = logging.getLogger(__name__)

class PracticeGenerator:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

    async def generate_sql_problem(self, difficulty: str = "medium") -> dict:
        """
        Dynamically generate a SQL practice problem using Groq AI.
        """
        if not self.client:
            logger.warning("Groq API key not configured for SQL generation.")
            return self._get_sql_fallback()

        topics = ["JOINs", "GROUP BY", "Subqueries", "Window Functions", "Aggregate Functions"]
        topic = random.choice(topics)

        prompt = f"""
        You are an expert SQL database interviewer. Generate a completely unique SQL practice question about {topic} with {difficulty} difficulty.
        Provide the response in a valid JSON object matching this structure EXACTLY:
        {{
            "question": "(The problem description, e.g. 'Write a query to find...')",
            "difficulty": "{difficulty}",
            "hint": "(A helpful hint for the user to solve the query)",
            "tables": [
                {{
                    "name": "(table name, e.g. users)",
                    "columns": [
                        {{ "name": "id", "type": "INT", "isPrimaryKey": true, "isForeignKey": false }},
                        {{ "name": "...", "type": "...", "isPrimaryKey": false, "isForeignKey": false }}
                    ]
                }}
            ],
            "mockResults": {{
                "columns": ["col1", "col2"],
                "rows": [
                    ["val1", "val2"],
                    ["val3", "val4"]
                ],
                "executionTime": "12ms",
                "optimizationScore": 90,
                "feedback": "(Feedback on how an optimal query would look and what to watch out for)"
            }}
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                response_format={"type": "json_object"},
                temperature=0.9,
            )
            data = json.loads(response.choices[0].message.content)
            # Ensure proper typing since Pydantic will serialize this directly as dict
            return data
        except Exception as e:
            logger.error(f"Error in dynamic SQL Generator: {e}")
            return self._get_sql_fallback()

    async def generate_debugging_problem(self, difficulty: str = "medium") -> dict:
        """
        Dynamically generate a debugging practice problem using Groq AI.
        """
        if not self.client:
            logger.warning("Groq API key not configured for Debugging generation.")
            return self._get_debugging_fallback()

        topics = ["Off-by-one error", "Null pointer exception", "Infinite loop", "Mutable default argument", "Variable scoping issue"]
        topic = random.choice(topics)
        languages = ["python", "javascript", "java"]
        language = random.choice(languages)

        prompt = f"""
        You are an expert code reviewer. Generate a completely unique debugging coding challenge in {language} about a '{topic}' issue, with {difficulty} difficulty.
        Provide the response in a valid JSON object matching this structure EXACTLY:
        {{
            "title": "(A catchy title for the bug)",
            "language": "{language}",
            "difficulty": "{difficulty}",
            "description": "(What the function is supposed to do, and a hint about the error)",
            "brokenCode": "(The source code with the bug inside)",
            "targetCode": "(The fixed source code)",
            "explanation": "(A clear explanation of why the bug occurred and how it was fixed)"
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                response_format={"type": "json_object"},
                temperature=0.9,
            )
            data = json.loads(response.choices[0].message.content)
            return data
        except Exception as e:
            logger.error(f"Error in dynamic Debugging Generator: {e}")
            return self._get_debugging_fallback()


    def _get_sql_fallback(self) -> dict:
        return {
            "question": "Write a query to find the total number of orders for each user, sorted by highest orders first.",
            "difficulty": "easy",
            "hint": "Assume there are two tables available: users and orders. You can assume the users table has an id and name, and the orders table has an id, user_id, and amount.",
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        { "name": "id", "type": "INT", "isPrimaryKey": True, "isForeignKey": False },
                        { "name": "name", "type": "VARCHAR", "isPrimaryKey": False, "isForeignKey": False }
                    ]
                },
                {
                    "name": "orders",
                    "columns": [
                        { "name": "id", "type": "INT", "isPrimaryKey": True, "isForeignKey": False },
                        { "name": "user_id", "type": "INT", "isPrimaryKey": False, "isForeignKey": True },
                        { "name": "amount", "type": "DECIMAL", "isPrimaryKey": False, "isForeignKey": False }
                    ]
                }
            ],
            "mockResults": {
                "columns": ["id", "name", "total_orders"],
                "rows": [
                    [1, "Alice Smith", 12],
                    [2, "Bob Johnson", 8]
                ],
                "executionTime": "15ms",
                "optimizationScore": 85,
                "feedback": "Good use of LEFT JOIN. Ensure there is an index on orders(user_id)."
            }
        }

    def _get_debugging_fallback(self) -> dict:
        return {
            "title": "Array Out of Bounds Exception",
            "language": "javascript",
            "difficulty": "easy",
            "description": "This function is supposed to sum all elements in an array. However, it is throwing an error or returning NaN. Can you find and fix the bug?",
            "brokenCode": "function sumArray(arr) {\n  let sum = 0;\n  for (let i = 0; i <= arr.length; i++) {\n    sum += arr[i];\n  }\n  return sum;\n}",
            "targetCode": "function sumArray(arr) {\n  let sum = 0;\n  for (let i = 0; i < arr.length; i++) {\n    sum += arr[i];\n  }\n  return sum;\n}",
            "explanation": "The loop condition used `<=` instead of `<`, causing an out of bounds access."
        }
