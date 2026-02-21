from fastapi import APIRouter
from app.api.v1.endpoints import auth, meetings, projects, tasks, websocket, attendance, transcripts, recordings

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
api_router.include_router(recordings.router, prefix="/recordings", tags=["recordings"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["attendance"])
api_router.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
