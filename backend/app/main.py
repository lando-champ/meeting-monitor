import asyncio
from typing import Optional

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

# Ensure CORS origins is always a list; include common dev origins (8080, 5173, 3000)
_default_origins = [
    "http://localhost:5173", "http://localhost:3000", "http://localhost:8080",
    "http://127.0.0.1:5173", "http://127.0.0.1:3000", "http://127.0.0.1:8080",
]
_cors_origins = list(settings.CORS_ORIGINS) if settings.CORS_ORIGINS else _default_origins.copy()
for origin in _default_origins:
    if origin not in _cors_origins:
        _cors_origins.append(origin)

# CORS for actual GET/POST etc (this runs second = inner)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)
# OPTIONS preflight - allow any localhost/127.0.0.1 origin
app.add_middleware(CORSPreflightMiddleware, allow_origins=_cors_origins)

# Include routers
app.include_router(api_router, prefix="/api/v1")

_stale_sweep_bg_task: Optional[asyncio.Task] = None


async def _run_periodic_stale_sweep(interval_hours: int) -> None:
    from app.core.database import get_database
    from app.services.task_stale_detection import mark_stale_tasks_all_projects

    interval_sec = max(60, int(interval_hours) * 3600)
    while True:
        try:
            db = await get_database()
            r = await mark_stale_tasks_all_projects(db)
            if r.get("marked"):
                print(f"✅ stale task sweep: marked {r.get('marked')} task(s)")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print("⚠️ stale task sweep failed:", e)
        await asyncio.sleep(interval_sec)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    # Validate Groq key by calling the API (so we know if key is rejected by Groq)
    if settings.GROQ_API_KEY and len(settings.GROQ_API_KEY) > 10:
        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            list(client.models.list())  # minimal call to validate key
            print("✅ GROQ_API_KEY valid (transcription enabled)")
        except Exception as e:
            err = str(e).lower()
            if "401" in err or "invalid" in err or "auth" in err:
                print("❌ GROQ_API_KEY rejected by Groq. Create a new key at https://console.groq.com and replace GROQ_API_KEY in backend/.env")
            else:
                print("⚠️ GROQ check failed:", e)
    else:
        print("⚠️ GROQ_API_KEY missing in backend/.env — live transcription disabled. Get a key at https://console.groq.com")
    await init_db()

    global _stale_sweep_bg_task
    bg_h = int(getattr(settings, "STALE_TASK_BACKGROUND_INTERVAL_HOURS", 0) or 0)
    if bg_h > 0:
        _stale_sweep_bg_task = asyncio.create_task(_run_periodic_stale_sweep(bg_h))
        print(
            f"✅ Stale task background sweep scheduled every {bg_h}h "
            "(requires STALE_TASK_AUTO_BLOCKERS_ENABLED=true to mark tasks)"
        )

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown"""
    global _stale_sweep_bg_task
    if _stale_sweep_bg_task and not _stale_sweep_bg_task.done():
        _stale_sweep_bg_task.cancel()
        try:
            await _stale_sweep_bg_task
        except asyncio.CancelledError:
            pass
    from app.core.database import close_db
    await close_db()

@app.get("/")
async def root():
    return {"message": "Meeting Monitor API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
