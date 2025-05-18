# app/schemas/user.py
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
)
from typing import Optional
from datetime import datetime
from beanie import PydanticObjectId
from app.db.models.enums import UserType, Gender


class UserBase(BaseModel):
    """Base schema for user attributes, used for creation and reading."""

    email: EmailStr = Field(examples=["user@example.com"])
    name: str = Field(min_length=1, max_length=100, examples=["New User"])
    age: Optional[int] = Field(default=None, ge=0, le=120, examples=[30])
    gender: Optional[Gender] = Field(default=None, examples=["other"])
    user_type: UserType = Field(
        default=UserType.PARENT, examples=[UserType.PARENT.value]
    )
    is_active: bool = Field(default=True, examples=[True])


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(min_length=8, examples=["ValidPassword123"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "newuser@example.com",
                "password": "ValidPassword123",
                "name": "New User",
                "age": 30,
                "gender": "other",
                "user_type": UserType.PARENT.value,
                "is_active": True,
            }
        }
    )


class UserUpdate(BaseModel):
    """Schema for updating an existing user. All fields are optional."""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, examples=["Updated Name"]
    )
    age: Optional[int] = Field(default=None, ge=0, le=120, examples=[30])
    gender: Optional[Gender] = Field(default=None, examples=["other"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"name": "Updated User Name", "age": 35, "gender": "female"}
        }
    )


class UserRead(UserBase):
    """Schema for reading user data, including the ID and timestamps."""

    id: str = Field(alias="_id", examples=["6810f23fa8a74c7e181b512d"])

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "id": "6810ed2f931f6f857012351d",
                "email": "test@example.com",
                "name": "Test User",
                "age": 30,
                "gender": "other",
                "user_type": UserType.PARENT.value,
                "is_active": True,
                "created_at": "2025-04-29T21:15:59.314Z",
                "updated_at": "2025-04-29T21:15:59.314Z",
            }
        },
    )


class UserPasswordUpdate(BaseModel):
    current_password: str = Field(..., examples=["MyCurrentPassword123"])
    new_password: str = Field(min_length=8, examples=["MyNewSecurePassword456"])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "oldPassword123",
                "new_password": "newStrongPassword456",
            }
        }
    )
