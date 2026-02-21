"""
Database seeding script for development
Creates initial users and projects for testing
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from passlib.context import CryptContext
from datetime import datetime
import asyncio

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

async def seed_database():
    """Seed database with initial development data"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    print("🌱 Seeding database...")
    
    # Clear existing data (optional - comment out if you want to keep data)
    # await db.users.delete_many({})
    # await db.projects.delete_many({})
    
    # Seed Users
    users_data = [
        {
            "name": "Sarah Chen",
            "email": "sarah.chen@company.com",
            "role": "manager",
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah",
            "hashed_password": hash_password("password123"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Michael Park",
            "email": "michael.park@company.com",
            "role": "member",
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Michael",
            "hashed_password": hash_password("password123"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Prof. James Wilson",
            "email": "prof.wilson@university.edu",
            "role": "teacher",
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=James",
            "hashed_password": hash_password("password123"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Emma Thompson",
            "email": "emma.thompson@university.edu",
            "role": "student",
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Emma",
            "hashed_password": hash_password("password123"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Alex Johnson",
            "email": "alex.johnson@university.edu",
            "role": "student",
            "avatar": "https://api.dicebear.com/7.x/avataaars/svg?seed=Alex",
            "hashed_password": hash_password("password123"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    # Insert users (skip if exists)
    user_ids = {}
    for user_data in users_data:
        existing = await db.users.find_one({"email": user_data["email"]})
        if existing:
            user_ids[user_data["email"]] = str(existing["_id"])
            print(f"  ✓ User already exists: {user_data['email']}")
        else:
            result = await db.users.insert_one(user_data)
            user_ids[user_data["email"]] = str(result.inserted_id)
            print(f"  ✓ Created user: {user_data['email']}")
    
    # Seed Workspaces (Corporate Projects)
    workspaces_data = [
        {
            "name": "Alpha Project",
            "description": "Core product development",
            "invite_code": "ALPHA2025",
            "project_type": "workspace",
            "owner_id": user_ids["sarah.chen@company.com"],
            "members": [
                user_ids["sarah.chen@company.com"],
                user_ids["michael.park@company.com"]
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Growth Team",
            "description": "Marketing and growth initiatives",
            "invite_code": "GROWTH2025",
            "project_type": "workspace",
            "owner_id": user_ids["sarah.chen@company.com"],
            "members": [user_ids["sarah.chen@company.com"]],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    # Insert workspaces
    workspace_ids = {}
    for workspace_data in workspaces_data:
        existing = await db.projects.find_one({"invite_code": workspace_data["invite_code"]})
        if existing:
            workspace_ids[workspace_data["invite_code"]] = str(existing["_id"])
            print(f"  ✓ Workspace already exists: {workspace_data['name']}")
        else:
            result = await db.projects.insert_one(workspace_data)
            workspace_ids[workspace_data["invite_code"]] = str(result.inserted_id)
            print(f"  ✓ Created workspace: {workspace_data['name']}")
    
    # Seed Classes (Education Projects)
    classes_data = [
        {
            "name": "Intro to Computer Science",
            "description": "Foundations of computing",
            "invite_code": "CS101",
            "project_type": "class",
            "owner_id": user_ids["prof.wilson@university.edu"],
            "members": [
                user_ids["prof.wilson@university.edu"],
                user_ids["emma.thompson@university.edu"],
                user_ids["alex.johnson@university.edu"]
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Data Structures",
            "description": "Core data structures and algorithms",
            "invite_code": "CS202",
            "project_type": "class",
            "owner_id": user_ids["prof.wilson@university.edu"],
            "members": [
                user_ids["prof.wilson@university.edu"],
                user_ids["emma.thompson@university.edu"]
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    # Insert classes
    class_ids = {}
    for class_data in classes_data:
        existing = await db.projects.find_one({"invite_code": class_data["invite_code"]})
        if existing:
            class_ids[class_data["invite_code"]] = str(existing["_id"])
            print(f"  ✓ Class already exists: {class_data['name']}")
        else:
            result = await db.projects.insert_one(class_data)
            class_ids[class_data["invite_code"]] = str(result.inserted_id)
            print(f"  ✓ Created class: {class_data['name']}")
    
    print("\n✅ Database seeding completed!")
    print("\n📝 Test Credentials:")
    print("  Manager: sarah.chen@company.com / password123")
    print("  Member: michael.park@company.com / password123")
    print("  Teacher: prof.wilson@university.edu / password123")
    print("  Student: emma.thompson@university.edu / password123")
    print("\n🔑 Invite Codes:")
    print("  Workspace: ALPHA2025, GROWTH2025")
    print("  Class: CS101, CS202")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
