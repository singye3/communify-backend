# app/schemas/admin.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.db.models.enums import UserType, UserStatus, Gender

# --- Schema for Admin Creating Any User ---
class AdminUserCreate(BaseModel):
    email: EmailStr = Field(..., examples=["new.admin@example.com"])
    password: str = Field(..., min_length=8, examples=["SecurePassword123"])
    name: str = Field(..., min_length=1, max_length=100, examples=["Admin Two"])
    user_type: UserType = Field(..., description="The type/role to assign to the new user.") 
    phone_number: Optional[str] = Field(default=None)
    age: Optional[int] = Field(default=None, gt=0, lt=150)
    gender: Optional[Gender] = Field(default=None)
    avatar_uri: Optional[str] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "another.admin@example.com",
                "password": "password1234",
                "name": "Another Admin",
                "user_type": "admin" # Can be "parent" or "child" too
            }
        }

# --- Schema for Admin Updating Any User ---
class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(default=None)
    user_type: Optional[UserType] = None # Allow admin to change type
    status: Optional[UserStatus] = None   # Allow admin to change status
    is_active: Optional[bool] = None # Allow admin to activate/deactivate
    age: Optional[int] = Field(default=None, gt=0, lt=150)
    gender: Optional[Gender] = None
    avatar_uri: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Name by Admin",
                "status": "inactive",
                "is_active": False
            }
        }