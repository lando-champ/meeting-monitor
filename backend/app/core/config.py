from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union

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

    # Jitsi (self-hosted)
    JITSI_DOMAIN: str = "https://meet.jit.si"
    
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
