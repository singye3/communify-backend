# app/db/database.py
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from pymongo.errors import ConnectionFailure, ConfigurationError

from app.core.config import settings
from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings

logger = logging.getLogger(__name__)

async def init_db():
    """
    Initialize Beanie ODM with MongoDB connection.
    Handles potential connection errors during startup.
    """
    logger.info("Attempting to initialize database connection...")

    if not settings.DATABASE_URL or not settings.DATABASE_NAME:
        logger.critical("CRITICAL ERROR: DATABASE_URL or DATABASE_NAME not configured in settings.")
        return 

    try:
        logger.info("Creating MongoDB client for URL (details omitted for security)...")
        client = AsyncIOMotorClient(
            settings.DATABASE_URL,
            serverSelectionTimeoutMS=15000, # Increased to 15 seconds
            connectTimeoutMS=15000,
            socketTimeoutMS=15000
            # Add TLS/SSL options if needed for specific environments/Atlas configs
            # tls=True,
            # tlsAllowInvalidCertificates=False, # Set to True only for local testing if needed
            # tlsCAFile=path/to/ca.pem
        )

        await client.admin.command('ismaster')
        logger.info("Successfully connected to MongoDB server.")

        database = client[settings.DATABASE_NAME]
        logger.info(f"Using database: '{settings.DATABASE_NAME}'")

        models_to_initialize = [
            User,
            ParentalSettings,
            AppearanceSettings,
        ]
        model_names = [model.__name__ for model in models_to_initialize]

        logger.info(f"Initializing Beanie with models: {model_names}")
        await init_beanie(
            database=database,
            document_models=models_to_initialize
        )
        logger.info("Beanie initialization complete.")

    except ConfigurationError as e:
        logger.critical("CRITICAL ERROR: MongoDB configuration error (e.g., invalid URI): %s", e, exc_info=True)
        raise RuntimeError(f"MongoDB Configuration Error: {e}") from e
    except ConnectionFailure as e:
        logger.critical("CRITICAL ERROR: Failed to connect to MongoDB server: %s", e, exc_info=True)
        raise RuntimeError(f"MongoDB Connection Failure: {e}") from e
    except Exception as e:
        logger.critical("CRITICAL ERROR: An unexpected error occurred during database initialization: %s", e, exc_info=True)
        raise RuntimeError(f"Unexpected Database Init Error: {e}") from e