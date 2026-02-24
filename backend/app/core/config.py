from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union, Optional

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "meeting_monitor"
    
    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Groq API
    GROQ_API_KEY: str = ""
    
    # CORS - accept list or comma-separated / JSON string from env
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Meeting bot: backend URL for WebSocket and API (bot connects here)
    # If not set in env, bot_manager will fall back to http://localhost:{PORT}
    BACKEND_URL: str = ""

    # Audio capture & STT (must match what bot sends)
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1
    AUDIO_CHUNK_SIZE: int = 1024
    # Input device for bot: system audio (e.g. "Stereo Mix" on Windows) not microphone.
    # Set to device name substring (e.g. "Stereo Mix", "What U Hear") or device index (e.g. "2").
    # Leave unset to use default input device (usually mic).
    AUDIO_INPUT_DEVICE: Optional[Union[int, str]] = None
    # STT buffer seconds before calling Whisper (smaller = faster first transcript, more API calls)
    STT_BUFFER_SECONDS: float = 3.0

    @field_validator("AUDIO_INPUT_DEVICE", mode="before")
    @classmethod
    def parse_audio_input_device(cls, v) -> Optional[Union[int, str]]:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        if isinstance(v, str) and v.strip().isdigit():
            return int(v.strip())
        return v if isinstance(v, (int, str)) else None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        import json
        if isinstance(v, list):
            # Env might give one element that is the whole JSON string
            if len(v) == 1 and isinstance(v[0], str) and v[0].strip().startswith("["):
                return json.loads(v[0])
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return []
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
