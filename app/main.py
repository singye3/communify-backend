# app/main.py
import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager

from app.core.logging_config import setup_logging
setup_logging()
# ---------------------------

from app.core.config import settings
from app.db.database import init_db
from app.api.v1.api import api_router, tags_metadata

# Get a logger for this module AFTER setup
logger = logging.getLogger(__name__) 

# --- Lifespan Context Manager ---
@asynccontextmanager
async def lifespan(app_instance: FastAPI): # Renamed app to app_instance to avoid conflict
    logger.info("Application starting up...") # Use logger
    await init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Application shutting down...")

# --- Define Security Schemes for OpenAPI Docs ---
bearer_scheme_docs = HTTPBearer(scheme_name="BearerAuth", description="Enter JWT token prefixed with 'Bearer '", auto_error=False)

# --- Create FastAPI App ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    openapi_extra={
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http", "scheme": "bearer", "bearerFormat": "JWT",
                    "description": "Enter JWT token (e.g., 'Bearer eyJ...')"
                }
            }
        }
    }
)

# --- CORS Middleware ---
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- Include API Routers ---
app.include_router(api_router, prefix=settings.API_V1_STR)

# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """Provides a simple welcome message for the API root."""
    logger.info("Root endpoint requested.") # Example log
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}
