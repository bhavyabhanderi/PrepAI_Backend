import io
import re
import asyncio
import logging
from gtts import gTTS
from groq import AsyncGroq
from app.config.config import settings

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        self.groq_api_key = settings.GROQ_API_KEY
        self.client = AsyncGroq(api_key=self.groq_api_key) if self.groq_api_key else None

    async def speech_to_text(self, audio_bytes: bytes, filename: str) -> str:
        """
        Uses Groq Whisper API for speech-to-text.
        """
        if not self.client:
            logger.warning("GROQ_API_KEY not set. Returning dummy transcription.")
            return "This is a dummy transcription because the Groq API key is missing. Uh, like, you know."

        def _get_extension(name: str) -> str:
            if not name:
                return "webm"
            parts = name.split(".")
            if len(parts) > 1:
                ext = parts[-1].lower()
                # Groq supports mp3, mp4, mpeg, mpga, m4a, wav, webm
                if ext in ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]:
                    return ext
            return "webm"

        try:
            ext = _get_extension(filename)
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = f"recording.{ext}"

            response = await self.client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3",
                response_format="json",
                language="en",
            )
            return response.text
        except Exception as e:
            logger.error(f"Groq STT Error: {e}")
            return "Error processing audio."

    async def text_to_speech(self, text: str) -> bytes:
        """
        Uses gTTS (Google Text-to-Speech) to synthesize text to MP3 bytes.
        """
        def _run():
            tts = gTTS(text=text, lang="en")
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue()

        try:
            return await asyncio.to_thread(_run)
        except Exception as e:
            logger.error(f"gTTS Error: {e}")
            return b""

    def analyze_voice_features(self, transcription: str, audio_duration_sec: float) -> dict:
        """
        Analyze the transcription for filler words, confidence, and speed.
        """
        # Calculate speed (Words Per Minute)
        words = transcription.split()
        word_count = len(words)
        speed_wpm = (word_count / audio_duration_sec) * 60 if audio_duration_sec > 0 else 0

        # Filler words detection
        filler_list = ["uh", "um", "like", "you know", "actually", "basically"]
        detected_fillers = []
        for filler in filler_list:
            # Case insensitive exact match or phrase match
            matches = re.findall(rf"\b{filler}\b", transcription.lower())
            for _ in matches:
                detected_fillers.append(filler)

        # Confidence logic (heuristic)
        # Penalize confidence based on filler words count and extreme speaking speeds
        confidence = 100
        confidence -= (len(detected_fillers) * 2)
        if speed_wpm < 100:
            confidence -= 10  # Too slow
        elif speed_wpm > 180:
            confidence -= 10  # Too fast

        confidence = max(0, min(100, confidence))  # clamp between 0-100

        # Pauses are harder to detect just from text, would ideally come from STT timestamps
        # We will estimate based on punctuation patterns for now
        pause_count = len(re.findall(r"\.\.\.|\-", transcription))

        return {
            "transcription": transcription,
            "speaking_speed_wpm": round(speed_wpm, 2),
            "words_per_minute": round(speed_wpm, 2),
            "confidence_score": confidence,
            "filler_words_detected": detected_fillers,
            "pause_detected_count": pause_count,
            "feedback": self._generate_feedback(speed_wpm, len(detected_fillers))
        }

    def _generate_feedback(self, wpm: float, filler_count: int) -> str:
        feedback = []
        if wpm < 100:
            feedback.append("Try to speak a bit faster to sound more energetic.")
        elif wpm > 180:
            feedback.append("You are speaking a bit too fast, try to slow down for clarity.")

        if filler_count > 3:
            feedback.append("Noticeable use of filler words. Try pausing instead of using 'um' or 'like'.")

        if not feedback:
            feedback.append("Great speaking pace and clarity!")

        return " ".join(feedback)

    async def voice_chat_first_question(self, job_role: str, job_description: str = None) -> str:
        """
        Generates the initial greeting and first question in a voice interview.
        """
        if not self.client:
            return f"Welcome to the voice interview! Let's begin: Tell me about your experience as a {job_role}."

        prompt = f"""
        You are a voice mock interviewer.
        The candidate is applying for the job role: {job_role}.
        {"Here is the job description: " + job_description if job_description else ""}
        
        Generate a welcoming greeting and a single first interview question.
        Keep the entire response very short (1 to 2 sentences max) so that it is conversational and clear when spoken aloud.
        """

        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=settings.GROQ_MODEL,
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq Voice Chat First Question Error: {e}")
            return f"Welcome to the voice interview! Let's begin: Tell me about your experience as a {job_role}."

    async def voice_chat(self, job_role: str, job_description: str = None, transcription: str = "", history: list = None) -> str:
        """
        Generates the next dynamic question/response in a voice interview.
        """
        if not self.client:
            return "That sounds interesting. Can you elaborate further on how you would handle that?"

        system_prompt = f"""
        You are an expert voice mock interviewer conducting a voice interview.
        The candidate is applying for the job role: {job_role}.
        {"Here is the job description: " + job_description if job_description else ""}
        
        Keep your response extremely concise (1 to 2 sentences max) so that it is natural and clear when converted to speech.
        Begin by briefly acknowledging the candidate's last answer, then ask the next relevant question for the job role.
        """

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history:
                messages.append({
                    "role": "user" if msg.get("role") == "user" else "assistant", 
                    "content": msg.get("text") or msg.get("content") or ""
                })
        messages.append({"role": "user", "content": transcription})

        try:
            response = await self.client.chat.completions.create(
                messages=messages,
                model=settings.GROQ_MODEL,
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Groq Voice Chat Error: {e}")
            return "Interesting point. What other technical skills or experiences make you a good fit for this role?"