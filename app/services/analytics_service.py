from fastapi import HTTPException, status, UploadFile
from app.models.analytics import PerformanceReport, LearningPlan
from app.models.interview import Interview, Answer
from app.models.coding import CodingSubmission
from app.ai.resume_analyzer import ResumeAnalyzer
from groq import AsyncGroq
from app.config.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        self.resume_analyzer = ResumeAnalyzer()

    async def generate_performance_report(self, user_id: str, interview_id: str) -> PerformanceReport:
        interview = await Interview.get(interview_id)
        if not interview or interview.user_id != user_id:
            raise HTTPException(status_code=404, detail="Interview not found")
            
        # Check if report already exists and delete to regenerate
        existing_report = await PerformanceReport.find_one(PerformanceReport.interview_id == interview_id)
        if existing_report:
            await existing_report.delete()
            try:
                from app.models.analytics import UserProgress
                existing_progress = await UserProgress.find_one(UserProgress.interview_id == interview_id)
                if existing_progress:
                    await existing_progress.delete()
            except Exception:
                pass
            
        # Aggregate scores from answers
        answers = await Answer.find(Answer.interview_id == interview_id).to_list()
        
        # Calculate technical score from answers
        tech_scores = [a.score for a in answers if a.score is not None]
        technical_score = sum(tech_scores) / len(tech_scores) if tech_scores else 0.0
        
        # Fetch coding submission if any (get the latest one)
        codings = await CodingSubmission.find(CodingSubmission.interview_id == interview_id).to_list()
        coding = codings[-1] if codings else None
        coding_score = coding.code_quality_score if coding and coding.code_quality_score else 0.0
        
        # We will mock communication/confidence/grammar as 80 for this example 
        # (in reality, these would come from the voice module's aggregated data)
        if len(answers) == 0 and not coding:
            communication_score = 0.0
            confidence_score = 0.0
            grammar_score = 0.0
            time_management_score = 0.0
        else:
            communication_score = 80.0
            confidence_score = 85.0
            grammar_score = 90.0
            time_management_score = 75.0
        
        # Overall average
        overall_score = (technical_score + coding_score + communication_score + confidence_score) / 4
        
        # Basic strengths/weaknesses inference
        strengths = []
        weaknesses = []
        if technical_score > 80: strengths.append("Strong Technical Knowledge")
        else: weaknesses.append("Technical Concepts need review")
        if coding_score > 80: strengths.append("Excellent Coding Quality")
        elif coding_score > 0: weaknesses.append("Code Optimization needed")
        
        report = PerformanceReport(
            user_id=user_id,
            interview_id=interview_id,
            overall_score=overall_score,
            communication_score=communication_score,
            technical_score=technical_score,
            coding_score=coding_score,
            confidence_score=confidence_score,
            grammar_score=grammar_score,
            time_management_score=time_management_score,
            strengths=strengths,
            weaknesses=weaknesses
        )
        await report.insert()

        try:
            from app.models.analytics import UserProgress
            progress = UserProgress(
                user_id=user_id,
                interview_id=interview_id,
                overall_score=overall_score,
                communication_score=communication_score,
                technical_score=technical_score,
                coding_score=coding_score,
                confidence_score=confidence_score,
                created_at=report.created_at
            )
            await progress.insert()
        except Exception as pe:
            logger.error(f"Error logging to UserProgress: {pe}")

        return report

    async def generate_learning_plan(self, user_id: str, report_id: str) -> LearningPlan:
        report = await PerformanceReport.get(report_id)
        if not report or report.user_id != user_id:
            raise HTTPException(status_code=404, detail="Report not found")
            
        existing_plan = await LearningPlan.find_one(LearningPlan.report_id == report_id)
        if existing_plan:
            return existing_plan
            
        # Ask AI to generate learning plan
        if not self.client:
            plan = LearningPlan(
                user_id=user_id,
                report_id=report_id,
                recommended_topics=["System Design", "Dynamic Programming"],
                practice_questions=[{"topic": "Arrays", "link": "https://leetcode.com/problemset/all/"}],
                youtube_resources=[],
                project_ideas=["Build a REST API"],
                weekly_schedule={"Week 1": [{"title": "Study Arrays", "type": "study", "done": False}]}
            )
            await plan.insert()
            return plan
            
        prompt = f"""
        Generate a personalized learning plan based on a candidate's interview performance.
        Weaknesses identified: {', '.join(report.weaknesses)}
        Overall Score: {report.overall_score}
        
        Output valid JSON exactly like this:
        {{
            "recommended_topics": ["topic1", "topic2"],
            "practice_questions": [{{"topic": "Name", "link": "url"}}],
            "youtube_resources": [{{"topic": "Name", "link": "url"}}],
            "project_ideas": ["idea1"],
            "weekly_schedule": {{"Week 1": ["Study Arrays", "Practice 2 sum"]}}
        }}
        """
        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            data = json.loads(response.choices[0].message.content)
            
            raw_schedule = data.get("weekly_schedule", {})
            schedule = {}
            for week, tasks in raw_schedule.items():
                if isinstance(tasks, list):
                    schedule[week] = [
                        {"title": t, "type": "study", "done": False} if isinstance(t, str) 
                        else {"title": t.get("title", str(t)), "type": t.get("type", "study"), "done": False} 
                        for t in tasks
                    ]

            plan = LearningPlan(
                user_id=user_id,
                report_id=report_id,
                recommended_topics=data.get("recommended_topics", []),
                practice_questions=data.get("practice_questions", []),
                youtube_resources=data.get("youtube_resources", []),
                project_ideas=data.get("project_ideas", []),
                weekly_schedule=schedule
            )
            await plan.insert()
            return plan
        except Exception as e:
            logger.error(f"Error generating learning plan: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate AI Learning Plan.")

    async def generate_learning_plan_from_resume(self, user_id: str, file: UploadFile) -> LearningPlan:
        # Check file extension
        if not file.filename.endswith((".pdf", ".docx")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and DOCX files are allowed."
            )
            
        try:
            parsed_text = await self.resume_analyzer.parse_resume_file(file)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse resume: {str(e)}")
            
        if not self.client:
            plan = LearningPlan(
                user_id=user_id,
                recommended_topics=["System Design", "Dynamic Programming"],
                practice_questions=[{"topic": "Arrays", "link": "https://leetcode.com/problemset/all/"}],
                youtube_resources=[],
                project_ideas=["Build a REST API"],
                weekly_schedule={"Week 1": [{"title": "Study Arrays", "type": "study", "done": False}]}
            )
            await plan.insert()
            return plan

        prompt = f"""
        Generate a personalized learning plan based on a candidate's resume to help them identify and fill skill gaps for tech roles.
        CRITICAL INSTRUCTIONS:
        1. Identify important modern tech skills missing from their resume (such as React Native, Android, iOS, Flutter, Java, Cloud, etc.) and dedicate specific weeks or tasks to learning them.
        2. For skills that ARE mentioned in the resume, suggest learning advanced, deep-dive topics for those specific skills.
        3. Provide a robust schedule: generate at least 4 to 6 tasks for every single week.
        4. Integrate platform practice: You MUST include tasks in the weekly schedule that tell the user to practice using this platform's built-in features. Use tasks like "Take a Technical Interview", "Solve a Coding Challenge", or "Take an Aptitude Test". Set the "type" field of these specific tasks to "interview", "coding", or "aptitude" respectively.

        Resume text: {parsed_text}
        
        Output valid JSON exactly like this:
        {{
            "recommended_topics": ["topic1"],
            "practice_questions": [{{"topic": "name", "link": "url"}}],
            "youtube_resources": [{{"topic": "name", "link": "url"}}],
            "project_ideas": ["idea1"],
            "weekly_schedule": {{"Week 1": [{{"title": "task name", "resource_name": "Video/Article Name", "resource_link": "https://url.com"}}]}}
        }}
        """
        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            data = json.loads(response.choices[0].message.content)
            
            raw_schedule = data.get("weekly_schedule", {})
            schedule = {}
            for week, tasks in raw_schedule.items():
                if isinstance(tasks, list):
                    schedule[week] = []
                    for t in tasks:
                        if isinstance(t, str):
                            schedule[week].append({"title": t, "type": "study", "done": False})
                        else:
                            task_obj = {
                                "title": t.get("title", str(t)),
                                "type": t.get("type", "study"),
                                "done": False
                            }
                            if "resource_name" in t and "resource_link" in t:
                                task_obj["resource"] = {"title": t["resource_name"], "link": t["resource_link"]}
                            schedule[week].append(task_obj)

            plan = LearningPlan(
                user_id=user_id,
                recommended_topics=data.get("recommended_topics", []),
                practice_questions=data.get("practice_questions", []),
                youtube_resources=data.get("youtube_resources", []),
                project_ideas=data.get("project_ideas", []),
                weekly_schedule=schedule
            )
            await plan.insert()
            return plan
        except Exception as e:
            logger.error(f"Error generating learning plan from resume: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate learning plan from resume")

    async def generate_skills_test(self, file: UploadFile) -> dict:
        """
        Parse the resume, detect top skills, then generate 10 MCQ questions per skill
        with difficulty labels: 4 Easy, 4 Medium, 2 Hard.
        """
        if not file.filename.endswith((".pdf", ".docx")):
            raise HTTPException(status_code=400, detail='Only PDF and DOCX files are allowed.')

        try:
            parsed_text = await self.resume_analyzer.parse_resume_file(file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f'Failed to parse resume: {str(e)}')

        if not self.client:
            return {
                'skills': ['Python'],
                'questions': [
                    {'id': 0, 'skill': 'Python', 'difficulty': 'easy',
                     'question': 'What does API stand for?',
                     'options': ['Application Programming Interface', 'Applied Program Index',
                                 'Application Process Integration', 'Auto Program Interface'],
                     'correct_answer': 'Application Programming Interface'}
                ]
            }

        # Step 1: Extract top skills from resume
        skill_prompt = (
            'From the following resume, identify the top 3 to 4 most important technical skills or technologies.\n'
            'Return ONLY a JSON object like: {"skills": ["React", "Python", "SQL"]}\n'
            f'Resume: {parsed_text[:2000]}'
        )
        skills = []
        try:
            skill_resp = await self.client.chat.completions.create(
                messages=[{'role': 'user', 'content': skill_prompt}],
                model=settings.GROQ_MODEL,
                response_format={'type': 'json_object'},
                temperature=0.3,
            )
            import json as _json
            skill_data = _json.loads(skill_resp.choices[0].message.content)
            skills = [str(s) for s in skill_data.get('skills', [])[:4]]
        except Exception as e:
            logger.error(f'Failed to extract skills: {e}')
            skills = ['Programming', 'Data Structures', 'Algorithms']

        if not skills:
            skills = ['Programming', 'Data Structures', 'Algorithms']

        # Step 2: For each skill, generate 10 questions (4 easy, 4 medium, 2 hard)
        all_questions = []
        qid = 0
        for skill in skills:
            q_prompt = (
                f'You are a technical interviewer. Generate EXACTLY 10 MCQ questions to test knowledge of "{skill}".\n'
                'Distribution: 4 Easy, 4 Medium, 2 Hard questions.\n'
                'Return ONLY this JSON format:\n'
                '{"questions": [{"question": "...", "difficulty": "easy", "options": ["A","B","C","D"], "correct_answer": "A"}]}\n'
                'Rules: exactly 10 questions, exactly 4 options each, correct_answer must exactly match one option, '
                f'questions must be specific and factual about {skill}.'
            )
            try:
                q_resp = await self.client.chat.completions.create(
                    messages=[{'role': 'user', 'content': q_prompt}],
                    model=settings.GROQ_MODEL,
                    response_format={'type': 'json_object'},
                    temperature=0.7,
                )
                q_data = _json.loads(q_resp.choices[0].message.content)
                raw_qs = q_data.get('questions', [])
                for q in raw_qs[:10]:
                    if isinstance(q, dict) and 'question' in q and 'options' in q and 'correct_answer' in q:
                        difficulty = str(q.get('difficulty', 'medium')).lower()
                        if difficulty not in ('easy', 'medium', 'hard'):
                            difficulty = 'medium'
                        all_questions.append({
                            'id': qid,
                            'skill': skill,
                            'difficulty': difficulty,
                            'question': str(q['question']),
                            'options': [str(o) for o in q['options'][:4]],
                            'correct_answer': str(q['correct_answer'])
                        })
                        qid += 1
            except Exception as e:
                logger.error(f'Failed to generate questions for skill {skill}: {e}')

        return {'skills': skills, 'questions': all_questions}

    async def generate_learning_plan_from_resume_with_score(
        self, user_id: str, file: UploadFile, quiz_score: int, weak_topics: list
    ) -> LearningPlan:
        """
        Generate a learning plan using both resume and quiz results to create a more targeted plan.
        """
        if not file.filename.endswith((".pdf", ".docx")):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed.")

        try:
            parsed_text = await self.resume_analyzer.parse_resume_file(file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse resume: {str(e)}")

        if not self.client:
            plan = LearningPlan(
                user_id=user_id,
                recommended_topics=weak_topics or ["Data Structures", "System Design"],
                practice_questions=[],
                youtube_resources=[],
                project_ideas=[],
                weekly_schedule={"Week 1": [{"title": "Review weak topics", "type": "study", "done": False}]}
            )
            await plan.insert()
            return plan

        score_level = "strong" if quiz_score >= 80 else ("moderate" if quiz_score >= 50 else "weak")
        weak_str = ", ".join(weak_topics) if weak_topics else "none identified"
        resume_snippet = parsed_text[:2000]

        prompt = (
            "Generate a deeply personalized learning plan using the candidate's resume AND their quiz performance.\n"
            "CRITICAL INSTRUCTIONS:\n"
            f"1. The candidate scored {quiz_score}% on the skills assessment overall ({score_level} level).\n"
            f"2. Here is their score breakdown per skill: {weak_str}. Dedicate the FIRST weeks to addressing the skills they scored poorly on.\n"
            "3. Identify important modern tech skills missing from the resume (React Native, Android, iOS, Flutter, Java, Cloud, etc.) and add weeks for them.\n"
            "4. For skills they scored well on (e.g. 8/10 or higher), suggest advanced deep-dive topics instead of basics.\n"
            "5. Generate at least 5 tasks per week for 4 weeks.\n"
            "6. Include platform practice tasks: 'Take a Technical Interview' (type: 'interview'), 'Solve a Coding Challenge' (type: 'coding'), or 'Take an Aptitude Test' (type: 'aptitude').\n"
            f"Resume: {resume_snippet}\n"
            "Output valid JSON exactly like this:\n"
            "{\"recommended_topics\": [\"topic1\"], \"practice_questions\": [{\"topic\": \"name\", \"link\": \"url\"}], "
            "\"youtube_resources\": [{\"topic\": \"name\", \"link\": \"url\"}], \"project_ideas\": [\"idea1\"], "
            "\"weekly_schedule\": {\"Week 1\": [{\"title\": \"task name\", \"type\": \"study\", \"resource_name\": \"Name\", \"resource_link\": \"https://url.com\"}]}}"
        )

        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            data = json.loads(response.choices[0].message.content)
            raw_schedule = data.get("weekly_schedule", {})
            schedule = {}
            for week, tasks in raw_schedule.items():
                if isinstance(tasks, list):
                    schedule[week] = []
                    for t in tasks:
                        if isinstance(t, str):
                            schedule[week].append({"title": t, "type": "study", "done": False})
                        else:
                            task_obj = {
                                "title": t.get("title", str(t)),
                                "type": t.get("type", "study"),
                                "done": False
                            }
                            if "resource_name" in t and "resource_link" in t:
                                task_obj["resource"] = {"title": t["resource_name"], "link": t["resource_link"]}
                            schedule[week].append(task_obj)

            plan = LearningPlan(
                user_id=user_id,
                recommended_topics=data.get("recommended_topics", []),
                practice_questions=data.get("practice_questions", []),
                youtube_resources=data.get("youtube_resources", []),
                project_ideas=data.get("project_ideas", []),
                weekly_schedule=schedule
            )
            await plan.insert()
            return plan
        except Exception as e:
            logger.error(f"Error generating learning plan with score: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate learning plan")

    async def get_dashboard_data(self, user_id: str) -> dict:
        """
        Calculate metrics for the main user dashboard.
        """
        from app.models.analytics import PerformanceReport
        from app.models.resume import ResumeAnalysis
        from app.models.interview import Interview
        from app.models.coding import CodingSubmission
        from datetime import datetime, timedelta

        reports = await PerformanceReport.find(PerformanceReport.user_id == user_id).to_list()
        resumes = await ResumeAnalysis.find(ResumeAnalysis.user_id == user_id).to_list()
        codings = await CodingSubmission.find(CodingSubmission.user_id == user_id).to_list()

        total_interviews = len(reports) + len(codings)
        latest_resume_score = resumes[-1].ats_score if resumes else 0
        
        from bson import ObjectId
        interview_ids = [r.interview_id for r in reports]
        obj_ids = []
        for iid in interview_ids:
            try:
                obj_ids.append(ObjectId(iid))
            except:
                pass
        interviews = await Interview.find({"_id": {"$in": obj_ids}}).to_list()
        interview_type_map = {str(i.id): i.type for i in interviews}

        tech_scores = [r.overall_score for r in reports if interview_type_map.get(r.interview_id) == "technical"]
        hr_scores = [r.overall_score for r in reports if interview_type_map.get(r.interview_id) == "hr"]
        
        # Add coding scores to technical score average
        coding_scores = [c.code_quality_score or 0 for c in codings]
        all_tech_scores = tech_scores + coding_scores

        tech_avg = sum(all_tech_scores) / len(all_tech_scores) if all_tech_scores else None
        hr_avg = sum(hr_scores) / len(hr_scores) if hr_scores else None
        has_resume = len(resumes) > 0

        stats = [
            {
                "label": "Total Interviews",
                "value": str(total_interviews),
                "change": f"+{total_interviews}" if total_interviews > 0 else "0",
                "up": True,
                "icon": "user-voice",
                "color": "#533086",
                "bg": "rgba(83,48,134,0.1)"
            },
            {
                "label": "Resume Score",
                "value": f"{latest_resume_score}%" if has_resume else "N/A",
                "change": "+5%" if has_resume else "0%",
                "up": True,
                "icon": "file-text",
                "color": "#FC9145",
                "bg": "rgba(252,145,69,0.1)"
            },
            {
                "label": "Technical Score",
                "value": f"{round(tech_avg)}%" if tech_avg is not None else "N/A",
                "change": "+2%" if tech_avg is not None else "0%",
                "up": True,
                "icon": "code",
                "color": "#4A4DC9",
                "bg": "rgba(74,77,201,0.1)"
            },
            {
                "label": "HR Score",
                "value": f"{round(hr_avg)}%" if hr_avg is not None else "N/A",
                "change": "0%",
                "up": True,
                "icon": "trophy",
                "color": "#22C55E",
                "bg": "rgba(34,197,94,0.1)"
            }
        ]

        # 2. Weekly Progress
        now = datetime.utcnow()
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        
        days_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekly_data = []
        for i in range(7):
            day_date = start_of_week + timedelta(days=i)
            next_day_date = day_date + timedelta(days=1)
            
            day_reports = [r for r in reports if day_date <= r.created_at < next_day_date]
            day_codings = [c for c in codings if day_date <= c.created_at < next_day_date]
            
            count = len(day_reports) + len(day_codings)
            
            scores_sum = sum(r.overall_score for r in day_reports) + sum(c.code_quality_score or 0 for c in day_codings)
            avg_score = scores_sum / count if count > 0 else 0
            
            weekly_data.append({
                "day": days_names[i],
                "interviews": count,
                "score": round(avg_score, 1)
            })

        # 3. Recent Activity
        activities = []
        for r in reports:
            itype = interview_type_map.get(r.interview_id, "Interview")
            activities.append({
                "id": f"report_{r.id}",
                "type": f"{itype.upper()} Interview",
                "score": round(r.overall_score or 0),
                "timestamp": r.created_at,
                "icon": "user-voice" if itype == "hr" else "code",
                "color": "#533086" if itype == "hr" else "#4A4DC9"
            })
        from app.models.syllabus import SavedSyllabus
        syllabi = await SavedSyllabus.find(SavedSyllabus.user_id == user_id).to_list()

        for res in resumes:
            activities.append({
                "id": f"resume_{res.id}",
                "type": "Resume Analysis",
                "score": res.ats_score,
                "timestamp": res.created_at,
                "icon": "file-text",
                "color": "#FC9145"
            })
        for c in codings:
            activities.append({
                "id": f"coding_{c.id}",
                "type": "Coding Test",
                "score": c.code_quality_score or 0,
                "timestamp": c.created_at,
                "icon": "code",
                "color": "#4A4DC9"
            })

        # Only include Interviews and Coding Tests in Recent Activity
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        recent_activity = []
        
        def _get_time_ago(dt: datetime) -> str:
            diff = datetime.utcnow() - dt
            if diff.days > 0:
                if diff.days == 1: return "Yesterday"
                return f"{diff.days} days ago"
            if diff.seconds > 3600:
                return f"{diff.seconds // 3600} hours ago"
            if diff.seconds > 60:
                return f"{diff.seconds // 60} minutes ago"
            return "Just now"

        for act in activities:
            recent_activity.append({
                "id": act["id"],
                "type": act["type"],
                "score": act["score"],
                "time": _get_time_ago(act["timestamp"]),
                "icon": act["icon"],
                "color": act["color"]
            })

        # 4. AI Suggestions
        ai_suggestions = []
        if reports:
            latest_report = reports[-1]
            if latest_report.weaknesses:
                ai_suggestions.append({
                    "text": f"Focus on {latest_report.weaknesses[0].lower()} — practicing can improve your score by 15%",
                    "type": "improvement"
                })
            else:
                ai_suggestions.append({
                    "text": "Great job in your last interview! Try a higher difficulty level to push yourself.",
                    "type": "praise"
                })
            if latest_report.overall_score >= 80:
                ai_suggestions.append({
                    "text": "Outstanding overall performance! Keep maintaining this quality.",
                    "type": "praise"
                })
            else:
                ai_suggestions.append({
                    "text": "Regular practice is key. Try to do at least 2 coding sessions a week.",
                    "type": "improvement"
                })
        else:
            ai_suggestions.append({
                "text": "Welcome! Complete your first resume analysis to unlock custom feedback.",
                "type": "improvement"
            })
            ai_suggestions.append({
                "text": "Prepare for your HR interviews by practicing common behavioral questions.",
                "type": "improvement"
            })

        return {
            "stats": stats,
            "weeklyData": weekly_data,
            "recentActivity": recent_activity,
            "aiSuggestions": ai_suggestions
        }

    async def get_performance_kpis(self, user_id: str) -> dict:
        """
        Calculate metrics for the Performance Screen.
        """
        from app.models.analytics import PerformanceReport
        from app.models.resume import ResumeAnalysis
        from app.models.interview import Interview

        reports = await PerformanceReport.find(PerformanceReport.user_id == user_id).to_list()
        resumes = await ResumeAnalysis.find(ResumeAnalysis.user_id == user_id).to_list()

        total_interviews = len(reports)
        overall_score = sum(r.overall_score for r in reports) / total_interviews if total_interviews > 0 else 0.0

        communication_avg = sum(r.communication_score for r in reports) / total_interviews if total_interviews > 0 else 0.0
        technical_avg = sum(r.technical_score for r in reports) / total_interviews if total_interviews > 0 else 0.0
        coding_avg = sum(r.coding_score for r in reports) / total_interviews if total_interviews > 0 else 0.0
        grammar_avg = sum(r.grammar_score for r in reports) / total_interviews if total_interviews > 0 else 0.0
        confidence_avg = sum(r.confidence_score for r in reports) / total_interviews if total_interviews > 0 else 0.0
        time_mgmt_avg = sum(r.time_management_score for r in reports) / total_interviews if total_interviews > 0 else 0.0

        # print("DEBUG AVERAGES:", type(communication_avg), type(technical_avg), type(coding_avg), flush=True)

        radar_data = [
            {"skill": "Communication", "score": round(communication_avg)},
            {"skill": "Technical", "score": round(technical_avg)},
            {"skill": "Coding", "score": round(coding_avg)},
            {"skill": "Grammar", "score": round(grammar_avg)},
            {"skill": "Confidence", "score": round(confidence_avg)},
            {"skill": "Time Mgmt", "score": round(time_mgmt_avg)}
        ]

        from bson import ObjectId
        interview_ids = [r.interview_id for r in reports]
        obj_ids = []
        for iid in interview_ids:
            try:
                obj_ids.append(ObjectId(iid))
            except:
                pass
        interviews = await Interview.find({"_id": {"$in": obj_ids}}).to_list()
        interview_type_map = {str(i.id): i.type for i in interviews}

        hr_scores = [r.overall_score for r in reports if interview_type_map.get(r.interview_id) == "hr"]
        tech_scores = [r.overall_score for r in reports if interview_type_map.get(r.interview_id) == "technical"]
        coding_scores = [r.overall_score for r in reports if interview_type_map.get(r.interview_id) == "coding"]
        voice_scores = [r.overall_score for r in reports if interview_type_map.get(r.interview_id) == "voice"]
        latest_resume_score = resumes[-1].ats_score if resumes else 0.0

        bar_data = [
            {"category": "HR", "score": round(sum(hr_scores) / len(hr_scores)) if hr_scores else 0},
            {"category": "Technical", "score": round(sum(tech_scores) / len(tech_scores)) if tech_scores else 0},
            {"category": "Coding", "score": round(sum(coding_scores) / len(coding_scores)) if coding_scores else 0},
            {"category": "Voice", "score": round(sum(voice_scores) / len(voice_scores)) if voice_scores else 0},
            {"category": "Resume", "score": round(latest_resume_score)}
        ]

        excel_cnt = sum(1 for r in reports if r.overall_score >= 90)
        good_cnt = sum(1 for r in reports if 75 <= r.overall_score < 90)
        avg_cnt = sum(1 for r in reports if 60 <= r.overall_score < 75)
        below_cnt = sum(1 for r in reports if r.overall_score < 60)

        pie_data = [
            {"name": "Excellent", "value": excel_cnt, "color": "#22C55E"},
            {"name": "Good", "value": good_cnt, "color": "#4A4DC9"},
            {"name": "Average", "value": avg_cnt, "color": "#FC9145"},
            {"name": "Below Avg", "value": below_cnt, "color": "#EF4444"}
        ]

        reports_chrono = sorted(reports, key=lambda x: x.created_at)
        progress_data = []
        for i, r in enumerate(reports_chrono):
            progress_data.append({
                "week": f"Int {i+1}",
                "score": round(r.overall_score, 1)
            })

        if not progress_data:
            progress_data = [
                {"week": "Start", "score": 0}
            ]

        return {
            "overall_score": round(overall_score, 1),
            "total_interviews": total_interviews,
            "radarData": radar_data,
            "barData": bar_data,
            "pieData": pie_data,
            "progressData": progress_data
        }

