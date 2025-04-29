# app/main.py
import logging
from fastapi import FastAPI # Removed Depends as it wasn't used here
from fastapi.middleware.cors import CORSMiddleware
# Removed HTTPBearer, HTTPAuthorizationCredentials as not directly used here
from contextlib import asynccontextmanager

# Setup logging first
from app.core.logging_config import setup_logging
setup_logging()
# ---------------------------

from app.core.config import settings
from app.db.database import init_db
from app.api.v1.api import api_router # api_router already aggregates endpoints

# Get a logger for this module AFTER setup
logger = logging.getLogger(__name__)

# --- Lifespan Context Manager ---
@asynccontextmanager
async def lifespan(app_instance: FastAPI): # Good practice to rename 'app' param
    """Handles application startup and shutdown events."""
    logger.info(f"Starting up {settings.PROJECT_NAME}...")
    try:
        await init_db() # Initialize database connection and Beanie models
        logger.info("Database initialization successful.")
    except Exception as e:
        # If init_db failed critically, it already raised RuntimeError.
        # Log any other potential lifespan startup errors.
        logger.critical(f"Critical error during application startup: {e}", exc_info=True)
        # Optionally raise here too, although init_db likely already stopped startup
        raise
    yield
    # --- Shutdown logic here (if any needed besides connection pool closing) ---
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


# --- OpenAPI Tags Metadata ---
# Define metadata for tags used in routers for richer documentation
tags_metadata = [
    {
        "name": "Authentication",
        "description": "User login (`/token`) and registration (`/register`).",
    },
    {
        "name": "Users - Current User (/me)",
        "description": "Operations related to the currently authenticated user (profile, password, deactivation).",
    },
    {
        "name": "Settings - User",
        "description": "Manage user-specific settings (Parental, Appearance). Requires authentication.",
    },
    {
        "name": "Admin - User Management",
        "description": "Operations for managing all users. Requires **Admin** privileges.",
    },
    {
        "name": "Root",
        "description": "API Root Endpoint.",
    },
]

# --- Create FastAPI App ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for Communify application, providing user management, settings, and core features.",
    version="1.0.0", # Example version
    openapi_url=f"{settings.API_V1_STR}/openapi.json", # Standard path for OpenAPI schema
    docs_url=f"{settings.API_V1_STR}/docs", # Standard path for Swagger UI
    redoc_url=f"{settings.API_V1_STR}/redoc", # Standard path for ReDoc
    lifespan=lifespan, # Use the defined lifespan manager
    openapi_tags=tags_metadata, # Provide tag metadata for docs
    # Define security scheme for OpenAPI docs (Swagger/ReDoc)
    openapi_extra={
        "components": {
            "securitySchemes": {
                "BearerAuth": { # Matches the name used in security dependencies
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Enter JWT token prefixed with 'Bearer ' (e.g., 'Bearer eyJhbGci...'). Obtain token via `/api/v1/auth/token`."
                }
            }
        }
    }
)

# --- CORS Middleware ---
# Enables Cross-Origin Resource Sharing if origins are configured
if settings.BACKEND_CORS_ORIGINS:
    # Ensure origins are strings, especially if using AnyHttpUrl in settings
    allow_origins_list = [str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS]
    logger.info(f"Configuring CORS for origins: {allow_origins_list}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins_list, # List of allowed origins
        allow_credentials=True, # Allow cookies/auth headers
        allow_methods=["*"], # Allow all standard methods (GET, POST, PUT, DELETE, etc.)
        allow_headers=["*"], # Allow all headers
    )
else:
    logger.info("CORS Middleware not configured (no origins specified in settings).")


# --- Include API Routers ---
# Mount the version 1 API router under the /api/v1 prefix
app.include_router(api_router, prefix=settings.API_V1_STR)
logger.info(f"Included API v1 router under prefix: {settings.API_V1_STR}")


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """Provides a simple welcome message for the API root."""
    logger.debug("Root endpoint '/' requested.")
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}

# --- Health Check Endpoint (Optional but Recommended) ---
@app.get("/health", tags=["Root"])
async def health_check():
    """Basic health check endpoint."""
    logger.debug("Health check endpoint '/health' requested.")
    # Add checks for DB connection etc. here if needed
    return {"status": "ok"}

# Note: Consider adding global exception handlers for cleaner error responses
# app.add_exception_handler(...)