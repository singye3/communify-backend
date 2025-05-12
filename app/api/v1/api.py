# app/api/v1/api.py
from fastapi import APIRouter
from app.api.v1.endpoints import auth
from app.api.v1.endpoints import users
from app.api.v1.endpoints import settings
from app.api.v1.endpoints import admin
from app.api.v1.endpoints import symbols
from app.api.v1.endpoints import user_symbols_customization

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(symbols.router, prefix="/symbols", tags=["Symbols & Categories"])
api_router.include_router(users.router, prefix="/users", tags=["Users - Current User (/me)"]) 
api_router.include_router(user_symbols_customization.router, prefix="/users/me/symbols", tags=["User Symbols Customization"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin - User Management"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings - User"]) 