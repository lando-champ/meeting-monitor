"""
Groq API service for Speech-to-Text and LLM operations
Will be implemented in Step 7-8
"""
from groq import Groq
from app.core.config import settings

class GroqService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using Groq STT"""
        # TODO: Implement in Step 7
        raise NotImplementedError("Will be implemented in Step 7")
    
    async def generate_summary(self, transcript: str) -> dict:
        """Generate meeting summary using Groq LLM"""
        # TODO: Implement in Step 8
        raise NotImplementedError("Will be implemented in Step 8")

groq_service = GroqService()
