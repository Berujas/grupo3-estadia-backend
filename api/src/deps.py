import os
from functools import lru_cache
from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://app:app@mongo:27017")
DB_NAME = os.getenv("DB_NAME", "ucchristus")

@lru_cache(maxsize=1)
def _client() -> MongoClient:
    # uuidRepresentation estándar para evitar warnings
    return MongoClient(MONGODB_URI, uuidRepresentation="standard")

def get_db():
    db = _client()[DB_NAME]
    try:
        yield db
    finally:
        # Con cliente cacheado no cerramos aquí
        pass
