from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api.v1.router import api_router
from app.middleware.cors_preflight import CORSPreflightMiddleware

app = FastAPI(
    title="Meeting Monitor API",
    description="Backend API for Meeting Monitor application",
    version="1.0.0",
)

# Ensure CORS origins is always a list (env can mis-parse)
_cors_origins = list(settings.CORS_ORIGINS) if settings.CORS_ORIGINS else ["http://localhost:5173", "http://localhost:8080", "http://127.0.0.1:5173", "http://127.0.0.1:8080"]

# CORS for actual GET/POST etc (this runs second = inner)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)
# OPTIONS preflight handler - added last so it runs FIRST and always returns 200
app.add_middleware(CORSPreflightMiddleware, allow_origins=_cors_origins)

# Include routers
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    from app.core.database import close_db
    await close_db()

@app.get("/")
async def root():
    return {"message": "Meeting Monitor API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
