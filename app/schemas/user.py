# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Annotated
from datetime import datetime

from app.db.models.enums import UserType

# --- Schema for Creating a User (Public Registration) ---
class UserCreate(BaseModel):
    """Schema for data required to create a new user via public registration."""
    email: EmailStr = Field(..., description="User's unique email address.", examples=["newuser@example.com"])
    password: str = Field(
        ...,
        min_length=8,
        description="User's password (must be at least 8 characters).",
        examples=["ValidPassword123"]
    )
    name: str = Field(..., min_length=1, max_length=100, description="User's display name.", examples=["New User"])

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "password123",
                "name": "New User"
            }
        }

# --- Schema for Creating an Admin User (Admin Endpoint) ---
class AdminUserCreate(UserCreate):
     """Schema for data required to create an admin user (used by admin endpoint)."""
     pass

# --- Schema for Updating User Profile (User's Own Profile) ---
class UserUpdate(BaseModel):
    """Schema for updating the current user's profile information. All fields are optional."""
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New display name for the user.",
        examples=["Updated Name"]
    )
    avatar_uri: Optional[str] = Field(
        default=None,
        description="New URI for the user's avatar image.",
        examples=["https://example.com/new_avatar.png"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated User Name",
                "avatar_uri": "https://example.com/new_avatar.png"
            }
        }

# --- Schema for Returning User Data (API Response) ---
class UserRead(BaseModel):
    """Schema for representing user data returned by the API."""
    id: str = Field(..., alias='_id', description="Unique user identifier.", examples=["6810f23fa8a74c7e181b512d"])
    email: EmailStr = Field(..., description="User's email address.", examples=["user@example.com"])
    name: str = Field(..., description="User's display name.", examples=["Test User"])
    avatar_uri: Optional[str] = Field(default=None, description="URI of the user's avatar image.", examples=["https://example.com/avatar.png"])
    is_active: bool = Field(..., description="Indicates if the user account is active.", examples=[True])
    user_type: UserType = Field(..., description="The role/type of the user (e.g., parent, admin).", examples=["parent"])
    created_at: datetime = Field(..., description="Timestamp when the user account was created.")
    updated_at: datetime = Field(..., description="Timestamp when the user account was last updated.")

    class Config:
        from_attributes = True
        populate_by_name = True 
        json_schema_extra = {
             "example": {
                "id": "6810ed2f931f6f857012351d",
                "email": "test@example.com",
                "name": "Test User",
                "avatar_uri": None,
                "is_active": True,
                "user_type": "parent",
                "created_at": "2025-04-29T21:15:59.314551Z",
                "updated_at": "2025-04-29T21:15:59.314551Z"
             }
        }