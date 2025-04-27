# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager # <--- Import asynccontextmanager

from app.core.config import settings
from app.db.database import init_db
from app.api.v1.api import api_router

# --- Lifespan Context Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Code to run on startup ---
    print("--- Application Starting Up ---")
    await init_db() # Initialize database connection
    print("--- Database Initialized ---")

    yield # --- Application runs here ---

    # --- Code to run on shutdown (optional) ---
    print("--- Application Shutting Down ---")
    # Add cleanup logic here if needed (e.g., close database client explicitly, though Motor often handles this)
    # Example: await close_db_client()

# --- Create FastAPI App with Lifespan ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan # <--- Pass the lifespan manager here
)

# Set all CORS enabled origins
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
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}