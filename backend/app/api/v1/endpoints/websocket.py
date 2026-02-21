from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.database import get_database
from typing import Dict
from datetime import datetime
import json

router = APIRouter()

# Store active WebSocket connections per meeting
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}  # {meeting_id: {user_id: websocket}}
    
    async def connect(self, websocket: WebSocket, meeting_id: str, user_id: str):
        await websocket.accept()
        if meeting_id not in self.active_connections:
            self.active_connections[meeting_id] = {}
        self.active_connections[meeting_id][user_id] = websocket
    
    def disconnect(self, meeting_id: str, user_id: str):
        if meeting_id in self.active_connections:
            self.active_connections[meeting_id].pop(user_id, None)
            if not self.active_connections[meeting_id]:
                del self.active_connections[meeting_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast_to_meeting(self, meeting_id: str, message: dict):
        if meeting_id in self.active_connections:
            for connection in self.active_connections[meeting_id].values():
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

@router.websocket("/meeting/{meeting_id}")
async def websocket_meeting(websocket: WebSocket, meeting_id: str, user_id: str):
    """
    WebSocket endpoint for meeting real-time features
    - Transcript streaming
    - Attendance updates
    - Participant presence
    """
    await manager.connect(websocket, meeting_id, user_id)
    
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "meeting_id": meeting_id,
            "user_id": user_id
        }, websocket)
        
        # Broadcast participant joined
        await manager.broadcast_to_meeting(meeting_id, {
            "type": "participant_joined",
            "user_id": user_id,
            "timestamp": str(datetime.utcnow())
        })
        
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "audio_chunk":
                # TODO: Process audio chunk and send to Groq STT (Step 7)
                pass
            
            elif data.get("type") == "transcript":
                # Save transcript to DB
                db = await get_database()
                await db.transcripts.insert_one({
                    "meeting_id": meeting_id,
                    "user_id": user_id,
                    "text": data.get("text"),
                    "timestamp": datetime.utcnow(),
                    "created_at": datetime.utcnow()
                })
                
                # Broadcast transcript to all participants
                await manager.broadcast_to_meeting(meeting_id, {
                    "type": "transcript_update",
                    "user_id": user_id,
                    "text": data.get("text"),
                    "timestamp": str(datetime.utcnow())
                })
            
            elif data.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong"
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(meeting_id, user_id)
        # Broadcast participant left
        await manager.broadcast_to_meeting(meeting_id, {
            "type": "participant_left",
            "user_id": user_id,
            "timestamp": str(datetime.utcnow())
        })
