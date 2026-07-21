from fastapi import UploadFile, HTTPException, status
import os
import aiofiles
from datetime import datetime
from app.models.resume import Resume, ResumeAnalysis
from app.ai.resume_analyzer import ResumeAnalyzer

class ResumeService:
    def __init__(self):
        self.upload_dir = "uploads/resumes"
        os.makedirs(self.upload_dir, exist_ok=True)
        self.analyzer = ResumeAnalyzer()

    async def upload_and_process_resume(self, user_id: str, file: UploadFile) -> ResumeAnalysis:
        # Check file extension
        if not file.filename.endswith((".pdf", ".docx")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF and DOCX files are allowed."
            )
            
        # Parse content
        try:
            parsed_text = await self.analyzer.parse_resume_file(file)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse resume: {str(e)}"
            )
            
        # Save file to disk securely
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        safe_filename = f"{user_id}_{timestamp}_{file.filename}"
        file_path = os.path.join(self.upload_dir, safe_filename)
        
        # Reset pointer again just in case
        await file.seek(0)
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            
        # Check for previous versions to increment version number
        existing_resumes = await Resume.find(Resume.user_id == user_id).sort("-version").to_list()
        version = existing_resumes[0].version + 1 if existing_resumes else 1
            
        # Invalidate previous resumes
        if existing_resumes:
            for r in existing_resumes:
                r.is_active = False
                await r.save()
            
        # Create Resume Record
        resume_record = Resume(
            user_id=user_id,
            file_name=file.filename,
            file_path=file_path,
            content_type=file.content_type,
            version=version,
            parsed_text=parsed_text
        )
        await resume_record.insert()
        
        # Analyze using AI
        analysis_result = await self.analyzer.analyze_resume(parsed_text)
        
        # Save Analysis
        resume_analysis = ResumeAnalysis(
            resume_id=str(resume_record.id),
            user_id=user_id,
            ats_score=analysis_result.get("ats_score", 0),
            grammar_score=analysis_result.get("grammar_score", 0),
            formatting_score=analysis_result.get("formatting_score", 0),
            missing_skills=analysis_result.get("missing_skills", []),
            recommended_skills=analysis_result.get("recommended_skills", []),
            resume_summary=analysis_result.get("resume_summary", ""),
            improvement_suggestions=analysis_result.get("improvement_suggestions", []),
            raw_ai_response=analysis_result
        )
        await resume_analysis.insert()
        
        return resume_analysis

    async def get_latest_resume_analysis(self, user_id: str) -> ResumeAnalysis:
        # Find active resume
        active_resume = await Resume.find_one(Resume.user_id == user_id, Resume.is_active == True)
        if not active_resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active resume found for user."
            )
            
        analysis = await ResumeAnalysis.find_one(ResumeAnalysis.resume_id == str(active_resume.id))
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found for active resume."
            )
        return analysis
