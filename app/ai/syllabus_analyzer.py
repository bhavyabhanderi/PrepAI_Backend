import PyPDF2
from fastapi import UploadFile
import io
import json
from groq import AsyncGroq
from app.config.config import settings
import logging

logger = logging.getLogger(__name__)
logging.getLogger("PyPDF2").setLevel(logging.ERROR)

class SyllabusAnalyzer:
    def __init__(self):
        # Initialize Groq client
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        
    async def parse_syllabus_file(self, file: UploadFile) -> str:
        """
        Extract text from PDF syllabus file.
        """
        content = await file.read()
        text = ""
        
        try:
            if file.filename.endswith(".pdf"):
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            else:
                raise ValueError("Unsupported file format. Please upload PDF.")
        except Exception as e:
            logger.error(f"Error parsing syllabus file: {e}")
            raise ValueError(f"Failed to parse syllabus file: {str(e)}")
            
        # Reset file pointer for any future reads
        await file.seek(0)
        return text.strip()

    async def analyze_syllabus(self, syllabus_text: str) -> dict:
        """
        Analyze syllabus text using Groq LLM to extract subject, chapters, and topics.
        """
        if not self.client:
            logger.error("Groq API key not configured. Cannot analyze syllabus.")
            raise ValueError("Groq API key not configured. Please add GROQ_API_KEY to your environment variables.")

        prompt = f"""
        You are an expert academic curriculum analyzer.
        Analyze the following syllabus text and extract the overall subject name, the chapters (or units), and the specific topics covered within each chapter.
        
        Syllabus Text:
        {syllabus_text}

        You MUST respond with a valid JSON object matching this exact structure:
        {{
            "subject": "Subject Name",
            "chapters": [
                {{
                    "chapter": "Chapter 1 Name",
                    "topics": [
                        "Topic 1",
                        "Topic 2"
                    ]
                }},
                {{
                    "chapter": "Chapter 2 Name",
                    "topics": [
                        "Topic 1"
                    ]
                }}
            ]
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
            logger.error(f"Groq API Error in SyllabusAnalyzer: {e}")
            raise ValueError(f"Failed to analyze syllabus: {str(e)}")
            
    async def chat_on_topic(self, topic: str, message: str, history: list) -> str:
        """
        Act as an AI tutor and respond to a student's question about a specific topic.
        """
        if not self.client:
            return f"I'm sorry, I am currently offline and cannot chat about '{topic}'. Please configure the Groq API key."

        system_prompt = (
            f"You are a helpful and knowledgeable AI tutor. Your role is to teach the student about the topic: '{topic}'. "
            "Provide clear, concise, and educational explanations. Do not answer questions that are completely unrelated to the topic."
        )

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history
        for msg in history:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            
        # Add the current message
        messages.append({"role": "user", "content": message})

        try:
            response = await self.client.chat.completions.create(
                messages=messages,
                model=settings.GROQ_MODEL,
                temperature=0.5,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API Error in chat_on_topic: {e}")
            return f"I encountered an error while communicating with the AI: {str(e)}"
