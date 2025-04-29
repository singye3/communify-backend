# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, settings 
from app.api.v1.endpoints import admin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"]) # Use a general "Settings" tag here for grouping in Swagger UI