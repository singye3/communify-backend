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
    logger.info("Attempting to initialize database connection...")

    if not settings.DATABASE_URL:
        logger.critical(
            "CRITICAL ERROR: DATABASE_URL not configured in settings. Database initialization cannot proceed."
        )
        raise RuntimeError("CRITICAL ERROR: DATABASE_URL is not set.")
    if not settings.DATABASE_NAME:
        logger.critical(
            "CRITICAL ERROR: DATABASE_NAME not configured in settings. Database initialization cannot proceed."
        )
        raise RuntimeError("CRITICAL ERROR: DATABASE_NAME is not set.")

    try:
        logger.info("Creating MongoDB client (URL details omitted for security)...")
        client = AsyncIOMotorClient(
            str(settings.DATABASE_URL),
            serverSelectionTimeoutMS=15000,
            connectTimeoutMS=15000,
            socketTimeoutMS=15000,
        )

        logger.info("Verifying MongoDB server connection...")
        await client.admin.command("ismaster")
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
        await init_beanie(database=database, document_models=models_to_initialize)
        logger.info("Beanie initialization complete. Database is ready.")

    except ConfigurationError as e:
        logger.critical(
            "CRITICAL ERROR: MongoDB configuration error (e.g., invalid URI format): %s",
            e,
            exc_info=True,
        )
        raise RuntimeError(f"MongoDB Configuration Error: {e}") from e
    except ConnectionFailure as e:
        logger.critical(
            "CRITICAL ERROR: Failed to connect to MongoDB server (check URL, credentials, network, server status): %s",
            e,
            exc_info=True,
        )
        raise RuntimeError(f"MongoDB Connection Failure: {e}") from e
    except Exception as e:
        exception_type = type(e).__name__
        logger.critical(
            "CRITICAL ERROR: An unexpected error of type '%s' occurred during database initialization: %s",
            exception_type,
            e,
            exc_info=True,
        )
        raise RuntimeError(
            f"Unexpected Database Init Error ({exception_type}): {e}"
        ) from e
