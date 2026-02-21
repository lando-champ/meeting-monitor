"""
Database collections schema definitions
Documents the structure of each MongoDB collection
"""
from typing import Dict, Any

# Collection schemas for reference
COLLECTIONS: Dict[str, Dict[str, Any]] = {
    "users": {
        "fields": {
            "_id": "ObjectId",
            "name": "string",
            "email": "string (unique, indexed)",
            "role": "string (manager|member|teacher|student)",
            "avatar": "string (optional)",
            "hashed_password": "string",
            "created_at": "datetime",
            "updated_at": "datetime"
        },
        "indexes": ["email", "role"]
    },
    "projects": {
        "fields": {
            "_id": "ObjectId",
            "name": "string",
            "description": "string (optional)",
            "invite_code": "string (unique, indexed)",
            "project_type": "string (workspace|class)",
            "owner_id": "string (user._id)",
            "members": "array[string] (user._id list)",
            "created_at": "datetime",
            "updated_at": "datetime"
        },
        "indexes": ["invite_code", "owner_id", "members", "project_type"]
    },
    "meetings": {
        "fields": {
            "_id": "ObjectId",
            "project_id": "string (project._id, indexed)",
            "room_name": "string (unique, indexed)",
            "type": "string (instant|scheduled)",
            "status": "string (scheduled|live|ended)",
            "start_time": "datetime (optional)",
            "created_by": "string (user._id)",
            "created_at": "datetime"
        },
        "indexes": ["room_name (unique)", "project_id", "status", "start_time", "(project_id, status)"]
    },
    "attendance": {
        "fields": {
            "_id": "ObjectId",
            "meeting_id": "string (meeting._id, indexed)",
            "user_id": "string (user._id, indexed)",
            "joined_at": "datetime",
            "left_at": "datetime (optional)",
            "duration": "integer (seconds, optional)",
            "created_at": "datetime"
        },
        "indexes": ["meeting_id", "user_id", "(meeting_id, user_id) unique"]
    },
    "transcripts": {
        "fields": {
            "_id": "ObjectId",
            "meeting_id": "string (meeting._id, indexed)",
            "user_id": "string (user._id, indexed)",
            "text": "string",
            "timestamp": "datetime (indexed)",
            "created_at": "datetime"
        },
        "indexes": ["meeting_id", "user_id", "timestamp", "(meeting_id, timestamp)"]
    },
    "tasks": {
        "fields": {
            "_id": "ObjectId",
            "project_id": "string (project._id, indexed)",
            "title": "string",
            "description": "string (optional)",
            "status": "string (todo|in-progress|review|done|blocked)",
            "priority": "string (low|medium|high|urgent)",
            "assignee_id": "string (user._id, optional, indexed)",
            "due_date": "datetime (optional)",
            "source_meeting_id": "string (meeting._id, optional, indexed)",
            "is_auto_generated": "boolean",
            "created_at": "datetime",
            "updated_at": "datetime",
            "completed_at": "datetime (optional)"
        },
        "indexes": [
            "project_id",
            "assignee_id",
            "status",
            "source_meeting_id",
            "(project_id, status)"
        ]
    },
    "documents": {
        "fields": {
            "_id": "ObjectId",
            "workspace_id": "string (project._id, indexed)",
            "name": "string (indexed)",
            "type": "string",
            "size": "string",
            "url": "string (optional, S3 or storage URL)",
            "modified": "string",
            "created_at": "datetime",
            "updated_at": "datetime"
        },
        "indexes": ["workspace_id", "name"]
    }
}
