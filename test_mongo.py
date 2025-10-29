from pymongo import MongoClient

try:
    client = MongoClient('mongodb://localhost:27017/')
    db_list = client.list_database_names()
    print("✅ MongoDB is running. Databases found:", db_list)
except Exception as e:
    print("❌ MongoDB connection failed:", e)