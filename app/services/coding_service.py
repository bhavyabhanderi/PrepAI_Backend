from fastapi import HTTPException, status
from app.models.coding import CodingSubmission
from app.schemas.coding import CodeExecutionRequest
from app.ai.code_reviewer import CodeReviewer
import asyncio
import subprocess
import time
import re
import sys
import tempfile
import os
import shutil

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

        # 1. Actual Code Execution
        execution_output = ""
        error_msg = None
        start_time = time.time()
        
        try:
            executable_code = data.source_code
            safe_stdin = data.stdin
            if safe_stdin and not safe_stdin.endswith('\n'):
                safe_stdin += '\n'
            
            if data.language.lower() == "python":
                # Remove prompts from input() to prevent them from printing to stdout
                executable_code = re.sub(r'input\(\s*(["\'])(.*?)\1\s*\)', 'input()', executable_code)
                
                process = subprocess.run(
                    [sys.executable, "-c", executable_code],
                    capture_output=True,
                    text=True,
                    input=safe_stdin if safe_stdin else None,
                    timeout=5
                )
                execution_output = process.stdout
                if process.stderr:
                    error_msg = process.stderr
            elif data.language.lower() == "javascript":
                # Remove prompts from rl.question() in node
                executable_code = re.sub(r'\.question\(\s*(["\'])(.*?)\1\s*,', '.question("",', executable_code)
                
                # Polyfill prompt() since it's a browser API, making it work synchronously via stdin
                js_polyfill = """
const fs = require('fs');
let __stdin_lines = [];
try { 
    __stdin_lines = fs.readFileSync(0, 'utf-8').split(/\\r?\\n/); 
} catch(e) {}
function prompt(msg) { 
    return __stdin_lines.shift() || ''; 
}
"""
                executable_code = js_polyfill + executable_code
                
                process = subprocess.run(
                    ["node", "-e", executable_code],
                    capture_output=True,
                    text=True,
                    input=safe_stdin if safe_stdin else None,
                    timeout=5
                )
                execution_output = process.stdout
                if process.stderr:
                    error_msg = process.stderr
            elif data.language.lower() in ["cpp", "c++"]:
                import tempfile
                import os
                try:
                    with tempfile.TemporaryDirectory() as temp_dir:
                        source_path = os.path.join(temp_dir, "main.cpp")
                        exe_path = os.path.join(temp_dir, "main.exe") if os.name == 'nt' else os.path.join(temp_dir, "main")
                        
                        with open(source_path, "w", encoding="utf-8") as f:
                            f.write(data.source_code)
                        
                        # Compile
                        compile_process = subprocess.run(
                            ["g++", source_path, "-o", exe_path],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if compile_process.returncode != 0:
                            error_msg = f"Compilation Error:\n{compile_process.stderr}"
                        else:
                            # Execute
                            process = subprocess.run(
                                [exe_path],
                                capture_output=True,
                                text=True,
                                input=safe_stdin if safe_stdin else None,
                                timeout=5
                            )
                            execution_output = process.stdout
                            if process.stderr:
                                error_msg = process.stderr
                except FileNotFoundError:
                    error_msg = "Execution Failed: C++ compiler (g++) not found on this system."
            elif data.language.lower() == "java":
                import tempfile
                import os
                import shutil
                try:
                    env = os.environ.copy()
                    if os.name == 'nt' and not shutil.which('javac'):
                        java_bin = r"C:\Program Files\Java\jdk-17\bin"
                        if os.path.exists(java_bin):
                            env["PATH"] = java_bin + os.pathsep + env["PATH"]
                            
                    with tempfile.TemporaryDirectory() as temp_dir:
                        source_path = os.path.join(temp_dir, "Main.java")
                        
                        with open(source_path, "w", encoding="utf-8") as f:
                            f.write(data.source_code)
                        
                        # Compile
                        compile_process = subprocess.run(
                            ["javac", source_path],
                            capture_output=True,
                            text=True,
                            env=env,
                            timeout=10
                        )
                        
                        if compile_process.returncode != 0:
                            error_msg = f"Compilation Error:\n{compile_process.stderr}"
                        else:
                            # Execute
                            process = subprocess.run(
                                ["java", "-cp", temp_dir, "Main"],
                                capture_output=True,
                                text=True,
                                input=safe_stdin if safe_stdin else None,
                                env=env,
                                timeout=5
                            )
                            execution_output = process.stdout
                            if process.stderr:
                                error_msg = process.stderr
                except FileNotFoundError:
                    error_msg = "Execution Failed: Java compiler (javac) or runtime not found on this system."
            else:
                execution_output = f"Execution for {data.language} is not yet supported in this environment.\nMock output: Hello, PrepAI!"
        except subprocess.TimeoutExpired:
            error_msg = "Execution Timed Out (5 seconds limit)."
        except Exception as e:
            error_msg = f"Execution Failed: {str(e)}"
            
        execution_time_ms = (time.time() - start_time) * 1000
        
        # We will mock the test cases logic for now but show real output
        total_tests = len(data.test_cases) if data.test_cases else 1
        passed_tests = total_tests if not error_msg else 0
        
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
            execution_time_ms=execution_time_ms,
            memory_used_kb=1024.0, # Mock metric
            status="passed" if passed_tests == total_tests else "failed",
            output=execution_output.strip() if execution_output else None,
            error_message=error_msg.strip() if error_msg else None,
            time_complexity=review.get("time_complexity"),
            space_complexity=review.get("space_complexity"),
            optimization_suggestions=review.get("optimization_suggestions", []),
            code_quality_score=review.get("code_quality_score", 0)
        )
        await submission.insert()
        return submission
