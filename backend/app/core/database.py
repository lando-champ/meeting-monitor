from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import asyncio

class Database:
    client: AsyncIOMotorClient = None

db = Database()

async def get_database():
    """Get database instance"""
    return db.client[settings.MONGODB_DB_NAME]

async def init_db():
    """Initialize database connection and create indexes"""
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    # Test connection
    await db.client.admin.command('ping')
    print(f"✅ Connected to MongoDB: {settings.MONGODB_DB_NAME}")
    
    # Create indexes
    await create_indexes()
    print("✅ Database indexes created")

async def create_indexes():
    """Create database indexes for performance"""
    database = db.client[settings.MONGODB_DB_NAME]
    
    # Users collection indexes
    await database.users.create_index("email", unique=True)
    await database.users.create_index("role")
    
    # Projects collection indexes
    await database.projects.create_index("invite_code", unique=True)
    await database.projects.create_index("owner_id")
    await database.projects.create_index("members")
    await database.projects.create_index("project_type")
    
    # Meetings collection indexes (Phase 1 lifecycle schema)
    await database.meetings.create_index("room_name", unique=True)
    await database.meetings.create_index("project_id")
    await database.meetings.create_index("status")
    await database.meetings.create_index("start_time")
    await database.meetings.create_index([("project_id", 1), ("status", 1)])
    
    # Attendance collection indexes
    await database.attendance.create_index("meeting_id")
    await database.attendance.create_index("user_id")
    await database.attendance.create_index([("meeting_id", 1), ("user_id", 1)], unique=True)
    
    # Transcripts collection indexes
    await database.transcripts.create_index("meeting_id")
    await database.transcripts.create_index("user_id")
    await database.transcripts.create_index("timestamp")
    await database.transcripts.create_index([("meeting_id", 1), ("timestamp", 1)])
    
    # Tasks collection indexes
    await database.tasks.create_index("project_id")
    await database.tasks.create_index("assignee_id")
    await database.tasks.create_index("status")
    await database.tasks.create_index("source_meeting_id")
    await database.tasks.create_index([("project_id", 1), ("status", 1)])
    
    # Documents collection indexes (for team member documents)
    await database.documents.create_index("workspace_id")
    await database.documents.create_index("name")

async def close_db():
    """Close database connection"""
    if db.client:
        db.client.close()
        print("✅ MongoDB connection closed")
