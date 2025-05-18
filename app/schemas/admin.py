# app/schemas/admin.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from app.db.models.enums import UserType, UserStatus, Gender


class AdminUserCreate(BaseModel):
    email: EmailStr = Field(..., examples=["new.admin@example.com"])
    password: str = Field(
        ...,
        min_length=8,
        examples=["SecurePassword123"],
        description="User's password (min 8 characters). Consider adding complexity rules.",
    )
    name: str = Field(..., min_length=1, max_length=100, examples=["Admin Two"])
    user_type: UserType = Field(
        ..., description="The type/role to assign to the new user."
    )
    phone_number: Optional[str] = Field(
        default=None,
        examples=["+15551234567"],
        description="User's phone number (consider E.164 format validation if needed).",
    )
    age: Optional[int] = Field(default=None, gt=0, lt=150, examples=[35])
    gender: Optional[Gender] = Field(default=None, examples=["female"])
    avatar_uri: Optional[str] = Field(
        default=None, examples=["https://example.com/avatar.png"]
    )
    is_active: Optional[bool] = Field(
        default=True, description="Set initial active status (defaults to True)"
    )
    status: Optional[UserStatus] = Field(
        default=UserStatus.ACTIVE, description="Set initial status (defaults to ACTIVE)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "email": "another.admin@example.com",
                "password": "password1234",
                "name": "Another Admin",
                "user_type": "admin",
                "phone_number": "+15559876543",
                "age": 40,
                "gender": "male",
                "is_active": True,
                "status": "active",
            }
        }


class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(default=None, min_length=5, max_length=25)
    user_type: Optional[UserType] = None
    status: Optional[UserStatus] = None
    is_active: Optional[bool] = None
    age: Optional[int] = Field(default=None, gt=0, lt=150)
    gender: Optional[Gender] = None
    avatar_uri: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Name by Admin",
                "status": "inactive",
                "is_active": False,
                "user_type": "parent",
                "phone_number": "+15551112233",
            }
        }
