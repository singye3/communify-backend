# app/main.py
from fastapi import FastAPI, Depends
# --- Import CORSMiddleware ---
from fastapi.middleware.cors import CORSMiddleware
# ----------------------------
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.database import init_db
from app.api.v1.api import api_router
from app.api.deps import oauth2_scheme # Keep import for dependencies

# --- Lifespan Context Manager (Keep as before) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Application Starting Up ---")
    await init_db()
    print("--- Database Initialized ---")
    yield
    print("--- Application Shutting Down ---")

# --- Define Security Schemes for OpenAPI Docs ---
bearer_scheme = HTTPBearer(scheme_name="BearerAuth", description="Enter JWT token prefixed with 'Bearer '")

# --- Create FastAPI App with refined OpenAPI components ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    openapi_extras={
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Enter JWT token (e.g., 'Bearer eyJ...') "
                },
            }
        },
        # Optional: Apply globally
        # "security": [{"BearerAuth": []}],
    }
)

# --- Set all CORS enabled origins ---
# This block now has CORSMiddleware defined
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
# -----------------------------------

# --- Include API Routers (Keep as before) ---
app.include_router(api_router, prefix=settings.API_V1_STR)

# --- Root Endpoint (Keep as before) ---
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

# --- Example Protected Route (Keep as before) ---
@app.get("/test-auth", tags=["Test Auth"])
async def test_authorization(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
     """Requires authorization via the 'Authorize' button using Bearer token."""
     return {"message": "Authorization successful via Bearer scheme!", "scheme": credentials.scheme, "token_prefix": credentials.credentials[:10] + "..."}
# -----------------------------------------------------------------