import PyPDF2
import docx
from fastapi import UploadFile
import io
import json
from groq import AsyncGroq
from app.config.config import settings
import logging

logger = logging.getLogger(__name__)

# Suppress PyPDF2 warnings (like "unknown widths") to keep terminal clean
logging.getLogger("PyPDF2").setLevel(logging.ERROR)

class ResumeAnalyzer:
    def __init__(self):
        # Initialize Groq client
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        
    async def parse_resume_file(self, file: UploadFile) -> str:
        """
        Extract text from PDF or DOCX file.
        """
        content = await file.read()
        text = ""
        
        try:
            if file.filename.endswith(".pdf"):
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            elif file.filename.endswith(".docx"):
                doc = docx.Document(io.BytesIO(content))
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
            else:
                raise ValueError("Unsupported file format. Please upload PDF or DOCX.")
        except Exception as e:
            logger.error(f"Error parsing file: {e}")
            raise ValueError(f"Failed to parse file: {str(e)}")
            
        # Reset file pointer for any future reads
        await file.seek(0)
        return text.strip()

    async def analyze_resume(self, resume_text: str) -> dict:
        """
        Analyze resume text using Groq LLM to get ATS score and suggestions.
        """
        if not self.client:
            logger.warning("Groq API key not configured. Returning dummy analysis.")
            return self._get_dummy_analysis()

        prompt = f"""
        You are an expert ATS (Applicant Tracking System) and Senior Technical Recruiter. 
        Analyze the following resume text and provide a structured JSON response evaluating its quality.

        Resume Text:
        {resume_text}

        You MUST respond with a valid JSON object matching this exact structure:
        {{
            "ats_score": (integer 0-100),
            "grammar_score": (integer 0-100),
            "formatting_score": (integer 0-100),
            "missing_skills": [(list of strings)],
            "recommended_skills": [(list of strings)],
            "resume_summary": "(string)",
            "improvement_suggestions": [(list of strings)]
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=settings.GROQ_MODEL,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return result_json
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return self._get_dummy_analysis()
            
    def _get_dummy_analysis(self) -> dict:
        return {
            "ats_score": 50,
            "grammar_score": 70,
            "formatting_score": 60,
            "missing_skills": ["Python", "FastAPI (Dummy)"],
            "recommended_skills": ["Docker", "MongoDB"],
            "resume_summary": "This is a fallback summary since Groq API is not configured.",
            "improvement_suggestions": ["Configure Groq API Key to get real analysis."]
        }
