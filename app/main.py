# app/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Setup logging first
from app.core.logging_config import setup_logging

setup_logging()
# ---------------------------

from app.core.config import settings
from app.db.database import init_db
from app.api.v1.api import api_router

# Get a logger for this module AFTER setup
logger = logging.getLogger(__name__)


# --- Lifespan Context Manager ---
@asynccontextmanager
async def lifespan(app_instance: FastAPI):  # Good practice to rename 'app' param
    """Handles application startup and shutdown events."""
    logger.info(f"Starting up {settings.PROJECT_NAME}...")
    try:
        await init_db()  # Initialize database connection and Beanie models
        logger.info("Database initialization successful.")
    except Exception as e:
        logger.critical(
            f"Critical error during application startup: {e}", exc_info=True
        )
        raise
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")


# --- OpenAPI Tags Metadata ---
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
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    openapi_extra={
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Enter JWT token prefixed with 'Bearer ' (e.g., 'Bearer eyJhbGci...'). Obtain token via `/api/v1/auth/token`.",
                }
            }
        }
    },
)

# --- CORS Middleware ---
if settings.BACKEND_CORS_ORIGINS:
    allow_origins_list = [
        str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS
    ]
    logger.info(f"Configuring CORS for origins: {allow_origins_list}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    logger.info("CORS Middleware not configured (no origins specified in settings).")


# --- Include API Routers ---
app.include_router(api_router, prefix=settings.API_V1_STR)
logger.info(f"Included API v1 router under prefix: {settings.API_V1_STR}")


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """Provides a simple welcome message for the API root."""
    logger.debug("Root endpoint '/' requested.")
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}


@app.get("/health", tags=["Root"])
async def health_check():
    """Basic health check endpoint."""
    logger.debug("Health check endpoint '/health' requested.")
    return {"status": "ok"}
