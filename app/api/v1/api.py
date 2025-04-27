# app/api/v1/api.py
from fastapi import APIRouter

from app.api.v1.endpoints import auth, parental_settings, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(parental_settings.router, prefix="/settings", tags=["Settings"])