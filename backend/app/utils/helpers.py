"""
Helper utilities
"""
from bson import ObjectId

def format_object_id(obj: dict) -> dict:
    """Convert MongoDB ObjectId to string"""
    if "_id" in obj:
        obj["id"] = str(obj["_id"])
        del obj["_id"]
    return obj
