import json
import random
import logging
from groq import AsyncGroq
from app.config.config import settings
from app.models.coding import CodingProblem

logger = logging.getLogger(__name__)

class CodingGenerator:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

    async def generate_problem(self) -> CodingProblem:
        """
        Dynamically generate a coding problem using Groq AI.
        """
        if not self.client:
            logger.warning("Groq API key not configured. Returning a random fallback problem.")
            return self._get_random_fallback()

        topics = ["Arrays", "Strings", "Linked Lists", "Hash Maps", "Stacks", "Queues", "Binary Search", "Two Pointers"]
        difficulties = ["Easy", "Medium", "Hard"]
        topic = random.choice(topics)
        difficulty = random.choice(difficulties)

        prompt = f"""
        You are an expert interviewer. Generate a brand new, highly unique, and completely randomized coding interview problem about {topic} with {difficulty} difficulty.
        Ensure the problem scenario and logic are different from generic standard problems, so that repeated requests always yield fresh, distinct challenges.
        
        Provide your response in a valid JSON object matching this structure EXACTLY:
        {{
            "title": "(problem title, e.g. Valid Parentheses)",
            "difficulty": "{difficulty}",
            "description": "(detailed Markdown formatting problem description)",
            "examples": [
                {{
                    "input": "...",
                    "output": "...",
                    "explanation": "..."
                }}
            ],
            "constraints": [
                "constraint 1",
                "constraint 2"
            ],
            "initial_templates": {{
                "javascript": "// Write your solution here\\nfunction solution(...) {{\\n  \\n}}",
                "python": "# Write your solution here\\ndef solution(...):\\n    pass",
                "java": "// Write your solution here\\nclass Solution {{\\n    public ... solve(...) {{\\n        \\n    }}\\n}}",
                "cpp": "// Write your solution here\\n#include <vector>\\nusing namespace std;\\n\\n... solution(...) {{\\n    \\n}}",
                "csharp": "// Write your solution here\\npublic class Solution {{\\n    public ... Solve(...) {{\\n        \\n    }}\\n}}",
                "go": "// Write your solution here\\nfunc solution(...) ... {{\\n    \\n}}",
                "ruby": "# Write your solution here\\ndef solution(...)\\n\\nend",
                "php": "<?php\\n// Write your solution here\\nfunction solution(...) {{\\n\\n}}"
            }},
            "test_cases": [
                {{
                    "input": "...",
                    "expected_output": "..."
                }}
            ]
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
            
            problem = CodingProblem(
                title=data.get("title", f"Dynamic {topic} Challenge"),
                difficulty=data.get("difficulty", difficulty),
                description=data.get("description", "Solve this algorithmic puzzle."),
                examples=data.get("examples", []),
                constraints=data.get("constraints", []),
                initial_templates=data.get("initial_templates", {}),
                test_cases=data.get("test_cases", [])
            )
            await problem.insert()
            return problem
        except Exception as e:
            logger.error(f"Error in dynamic CodingGenerator: {e}")
            return self._get_random_fallback()

    def _get_random_fallback(self) -> CodingProblem:
        fallbacks = [
            {
                "title": "Reverse String",
                "difficulty": "Easy",
                "description": "Write a function that reverses a string. The input string is given as an array of characters.",
                "examples": [
                    {"input": 's = ["h","e","l","l","o"]', "output": '["o","l","l","e","h"]', "explanation": ""}
                ],
                "constraints": ["1 <= s.length <= 10^5", "s[i] is a printable ascii character."],
                "initial_templates": {
                    "javascript": "// Write your solution here\nfunction solution(s) {\n  \n}",
                    "python": "# Write your solution here\ndef solution(s):\n    pass",
                    "java": "// Write your solution here\nclass Solution {\n    public void solve(char[] s) {\n        \n    }\n}",
                    "cpp": "// Write your solution here\n#include <vector>\nusing namespace std;\n\nvoid solution(vector<char>& s) {\n    \n}",
                    "csharp": "// Write your solution here\npublic class Solution {\n    public void Solve(char[] s) {\n        \n    }\n}",
                    "go": "// Write your solution here\nfunc solution(s []byte) {\n    \n}",
                    "ruby": "# Write your solution here\ndef solution(s)\n\nend",
                    "php": "<?php\n// Write your solution here\nfunction solution($s) {\n\n}"
                },
                "test_cases": [
                    {"input": '["h","e","l","l","o"]', "expected_output": '["o","l","l","e","h"]'}
                ]
            },
            {
                "title": "Palindrome Number",
                "difficulty": "Easy",
                "description": "Given an integer `x`, return `true` if `x` is a palindrome, and `false` otherwise.",
                "examples": [
                    {"input": "x = 121", "output": "true", "explanation": "121 reads as 121 from left to right and from right to left."},
                    {"input": "x = -121", "output": "false", "explanation": "From left to right, it reads -121. From right to left, it becomes 121-."}
                ],
                "constraints": ["-2^31 <= x <= 2^31 - 1"],
                "initial_templates": {
                    "javascript": "// Write your solution here\nfunction solution(x) {\n  \n}",
                    "python": "# Write your solution here\ndef solution(x):\n    pass",
                    "java": "// Write your solution here\nclass Solution {\n    public boolean solve(int x) {\n        return false;\n    }\n}",
                    "cpp": "// Write your solution here\nbool solution(int x) {\n    return false;\n}"
                },
                "test_cases": [
                    {"input": "121", "expected_output": "true"},
                    {"input": "-121", "expected_output": "false"}
                ]
            }
        ]
        chosen = random.choice(fallbacks)
        return CodingProblem(
            title=chosen["title"],
            difficulty=chosen["difficulty"],
            description=chosen["description"],
            examples=chosen["examples"],
            constraints=chosen["constraints"],
            initial_templates=chosen["initial_templates"],
            test_cases=chosen["test_cases"]
        )
