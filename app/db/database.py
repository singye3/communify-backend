# app/db/database.py
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from pymongo.errors import ConnectionFailure, ConfigurationError

# Assuming settings are correctly defined elsewhere
from app.core.config import settings
# Import your Beanie models
from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings

logger = logging.getLogger(__name__)

async def init_db():
    """
    Initialize Beanie ODM with MongoDB connection.
    Handles potential connection errors during startup and raises RuntimeError on failure.
    """
    logger.info("Attempting to initialize database connection...")

    # --- Configuration Validation ---
    if not settings.DATABASE_URL:
        logger.critical("CRITICAL ERROR: DATABASE_URL not configured in settings. Database initialization cannot proceed.")
        # Raise error to prevent application startup without DB URL
        raise RuntimeError("CRITICAL ERROR: DATABASE_URL is not set.")
    if not settings.DATABASE_NAME:
         logger.critical("CRITICAL ERROR: DATABASE_NAME not configured in settings. Database initialization cannot proceed.")
         # Raise error to prevent application startup without DB Name
         raise RuntimeError("CRITICAL ERROR: DATABASE_NAME is not set.")

    try:
        logger.info("Creating MongoDB client (URL details omitted for security)...")
        # --- Client Creation ---
        client = AsyncIOMotorClient(
            str(settings.DATABASE_URL), # Ensure URL is a string if using PydanticUrl type
            serverSelectionTimeoutMS=15000, # Time to find a suitable server
            connectTimeoutMS=15000,         # Time to establish initial connection
            socketTimeoutMS=15000           # Time for socket operations
            # Add TLS/SSL options if needed for specific environments/Atlas configs
            # tls=True,
            # tlsAllowInvalidCertificates=False, # Set to True only for local testing if needed
            # tlsCAFile=path/to/ca.pem
        )

        # --- Connection Verification ---
        # Verify connection by running a simple command ('ismaster' or 'ping')
        logger.info("Verifying MongoDB server connection...")
        await client.admin.command('ismaster') # Or 'ping'
        logger.info("Successfully connected to MongoDB server.")

        # --- Database Selection ---
        database = client[settings.DATABASE_NAME]
        logger.info(f"Using database: '{settings.DATABASE_NAME}'")

        # --- Beanie Initialization ---
        models_to_initialize = [
            User,
            ParentalSettings,
            AppearanceSettings,
            # Add any other Beanie Document models here
        ]
        model_names = [model.__name__ for model in models_to_initialize]

        logger.info(f"Initializing Beanie with models: {model_names}")
        await init_beanie(
            database=database,
            document_models=models_to_initialize
        )
        logger.info("Beanie initialization complete. Database is ready.")

    # --- Specific Error Handling ---
    except ConfigurationError as e:
        logger.critical("CRITICAL ERROR: MongoDB configuration error (e.g., invalid URI format): %s", e, exc_info=True)
        raise RuntimeError(f"MongoDB Configuration Error: {e}") from e
    except ConnectionFailure as e:
        # This catches errors during the connection attempt (e.g., server down, network issues, auth failure)
        logger.critical("CRITICAL ERROR: Failed to connect to MongoDB server (check URL, credentials, network, server status): %s", e, exc_info=True)
        raise RuntimeError(f"MongoDB Connection Failure: {e}") from e
    # --- Generic Error Handling ---
    except Exception as e:
        # Catch any other unexpected errors during the process
        exception_type = type(e).__name__
        logger.critical(
            "CRITICAL ERROR: An unexpected error of type '%s' occurred during database initialization: %s",
            exception_type, e, exc_info=True
        )
        raise RuntimeError(f"Unexpected Database Init Error ({exception_type}): {e}") from e

# Note: The client object ('client') created here is typically managed by Motor's connection pool
# and doesn't usually need explicit closing in the init function itself.
# Lifespan management (if needed) is often handled at the FastAPI app level.