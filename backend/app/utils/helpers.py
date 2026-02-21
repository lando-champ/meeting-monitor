"""
Helper utilities
"""
from bson import ObjectId
from datetime import datetime

def generate_jitsi_room_name(project_id: str, meeting_title: str) -> str:
    """Generate a unique Jitsi room name"""
    import hashlib
    room_str = f"{project_id}-{meeting_title}-{datetime.utcnow().isoformat()}"
    room_hash = hashlib.md5(room_str.encode()).hexdigest()[:12]
    return f"meeting-{room_hash}"

def format_object_id(obj: dict) -> dict:
    """Convert MongoDB ObjectId to string"""
    if "_id" in obj:
        obj["id"] = str(obj["_id"])
        del obj["_id"]
    return obj
