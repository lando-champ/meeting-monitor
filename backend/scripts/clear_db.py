"""
Clear all data from the meeting_monitor database.
Run with: python -m scripts.clear_db
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


COLLECTIONS = [
    "users",
    "projects",
    "meetings",
    "attendance",
    "transcripts",
    "tasks",
    "documents",
]


async def clear_database():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]

    print(f"Clearing all data in database: {settings.MONGODB_DB_NAME}\n")

    for name in COLLECTIONS:
        try:
            result = await db[name].delete_many({})
            print(f"   {name}: deleted {result.deleted_count} document(s)")
        except Exception as e:
            print(f"   {name}: skip ({e})")

    client.close()
    print("\nDone. Database cleared. Restart the server to recreate indexes if needed.")


if __name__ == "__main__":
    asyncio.run(clear_database())
