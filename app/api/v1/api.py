# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import users
from app.api.v1.endpoints import settings
from app.api.v1.endpoints import admin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users - Current User (/me)"]) # Refined tag to be more specific
api_router.include_router(admin.router, prefix="/admin", tags=["Admin - User Management"]) # Refined tag
api_router.include_router(settings.router, prefix="/settings", tags=["Settings - User"]) # Refined tag