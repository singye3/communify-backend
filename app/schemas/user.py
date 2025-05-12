# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

from app.db.models.enums import UserType, Gender


class UserCreate(BaseModel):
    email: EmailStr = Field(..., examples=["newuser@example.com"])
    password: str = Field(
        ...,
        min_length=8,
        examples=["ValidPassword123"]
    )
    name: str = Field(..., min_length=1, max_length=100, examples=["New User"])
    age: Optional[int] = Field(
        default=None,
        ge=0,
        le=120,
        examples=[30]
    )
    gender: Optional[Gender] = Field(
        default=None,
        examples=["other"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "password123",
                "name": "New User",
                "age": 30,
                "gender": "other"
            }
        }


class UserUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        examples=["Updated Name"]
    )
    age: Optional[int] = Field(
        default=None,
        ge=0,
        le=120,
        examples=[30]
    )
    gender: Optional[Gender] = Field(
        default=None,
        examples=["other"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated User Name",
                "age": 30,
                "gender": "other"
            }
        }


class UserRead(BaseModel):
    id: str = Field(..., alias='_id', examples=["6810f23fa8a74c7e181b512d"])
    email: EmailStr = Field(..., examples=["user@example.com"])
    name: str = Field(..., examples=["Test User"])
    is_active: bool = Field(..., examples=[True])
    user_type: UserType = Field(..., examples=["parent"])
    created_at: datetime
    updated_at: datetime
    age: Optional[int] = Field(
        default=None,
        ge=0,
        le=120,
        examples=[30]
    )
    gender: Optional[Gender] = Field(
        default=None,
        examples=["other"]
    )

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "6810ed2f931f6f857012351d",
                "email": "test@example.com",
                "name": "Test User",
                "is_active": True,
                "user_type": "parent",
                "created_at": "2025-04-29T21:15:59.314Z",
                "updated_at": "2025-04-29T21:15:59.314Z",
                "age": 30,
                "gender": "other"
            }
        }


class UserPasswordUpdate(BaseModel):
    current_password: str = Field(..., examples=["MyCurrentPassword123"])
    new_password: str = Field(
        ...,
        min_length=8,
        examples=["MyNewSecurePassword456"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "oldPassword123",
                "new_password": "newStrongPassword456"
            }
        }