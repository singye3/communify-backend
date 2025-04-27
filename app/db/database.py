# app/db/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings

# --- Import ONLY the models you are keeping ---
from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings
# ---------------------------------------------

async def init_db():
    """Initialize Beanie ODM with MongoDB connection."""
    print(f"Attempting to connect to MongoDB at {settings.DATABASE_URL}...")
    client = AsyncIOMotorClient(
        settings.DATABASE_URL,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    database = client[settings.DATABASE_NAME]

    # --- Update the list of models ---
    models_to_initialize = [
            User,
            ParentalSettings,
            AppearanceSettings, # Keep this one
        ]
    # ---------------------------------

    await init_beanie(
        database=database,
        document_models=models_to_initialize
    )
    print(f"Successfully connected to MongoDB database: {settings.DATABASE_NAME}")
    print(f"Initialized Beanie with models: {[model.__name__ for model in models_to_initialize]}")