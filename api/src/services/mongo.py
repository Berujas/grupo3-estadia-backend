import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://app:app@mongo:27017/?authSource=admin")
DB_NAME      = os.getenv("MONGODB_DB", "ucchristus")
COLL_NAME    = os.getenv("MONGODB_COLLECTION", "estadias")

_client = None

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI)
    return _client

def get_collection():
    return get_client()[DB_NAME][COLL_NAME]

def get_named_collection(name: str):
    return get_client()[DB_NAME][name]
