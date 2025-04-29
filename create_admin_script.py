# create_admin_script.py (Run this locally, NOT part of the API)
import asyncio
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv() 

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- CONFIGURATION ---
MONGO_DETAILS = os.getenv("DATABASE_URL")
DB_NAME = os.getenv("DATABASE_NAME")
ADMIN_EMAIL = "admin@communify.app" # Choose your admin email
ADMIN_PASSWORD = "admin123" # Choose a STRONG password
ADMIN_NAME = "App Admin"
# --- END CONFIGURATION ---

def get_password_hash(password):
    return pwd_context.hash(password)

async def create_first_admin():
    print(f"Connecting to {MONGO_DETAILS}...")
    client = AsyncIOMotorClient(MONGO_DETAILS)
    db = client[DB_NAME]
    user_collection = db["users"] # Collection name from model

    print(f"Checking if admin user '{ADMIN_EMAIL}' exists...")
    existing = await user_collection.find_one({"email": ADMIN_EMAIL})

    if existing:
        print("Admin user already exists.")
    else:
        print("Creating admin user...")
        hashed_password = get_password_hash(ADMIN_PASSWORD)
        admin_doc = {
            "email": ADMIN_EMAIL,
            "name": ADMIN_NAME,
            "hashed_password": hashed_password,
            "user_type": "admin", # Make sure this matches your enum value
            "status": "active",   # Make sure this matches your enum value
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            # Add other fields with defaults if necessary (phone, age, gender, avatar...)
            "phone_number": None,
            "age": None,
            "gender": None,
            "avatar_uri": None,
            "favorite_phrases": []
        }
        result = await user_collection.insert_one(admin_doc)
        print(f"Admin user created successfully with ID: {result.inserted_id}")

    client.close()

if __name__ == "__main__":
     # Need datetime for the script
    from datetime import datetime
    print("Running admin creation script...")
    asyncio.run(create_first_admin())
    print("Script finished.")