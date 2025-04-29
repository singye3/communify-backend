# app/schemas/admin.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from app.db.models.enums import UserType, UserStatus, Gender 

# --- Schema for Admin Creating Any User ---
class AdminUserCreate(BaseModel):
    email: EmailStr = Field(..., examples=["new.admin@example.com"])
    password: str = Field(..., min_length=8, examples=["SecurePassword123"], description="User's password (min 8 characters). Consider adding complexity rules.")
    name: str = Field(..., min_length=1, max_length=100, examples=["Admin Two"])
    user_type: UserType = Field(..., description="The type/role to assign to the new user.") # Required field
    # Include other optional fields from User model that admin can set at creation
    phone_number: Optional[str] = Field(default=None, examples=["+15551234567"], description="User's phone number (consider E.164 format validation if needed).")
    age: Optional[int] = Field(default=None, gt=0, lt=150, examples=[35])
    gender: Optional[Gender] = Field(default=None, examples=["female"])
    avatar_uri: Optional[str] = Field(default=None, examples=["https://example.com/avatar.png"])
    is_active: Optional[bool] = Field(default=True, description="Set initial active status (defaults to True)")
    status: Optional[UserStatus] = Field(default=UserStatus.ACTIVE, description="Set initial status (defaults to ACTIVE)")


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
                "status": "active"
            }
        }

# --- Schema for Admin Updating Any User ---
class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    # Email updates are complex (verification needed), generally avoided in simple PATCH
    # email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(default=None, min_length=5, max_length=25) # Added length constraint example
    user_type: Optional[UserType] = None # Allow admin to change type
    status: Optional[UserStatus] = None   # Allow admin to change status
    is_active: Optional[bool] = None # Allow admin to activate/deactivate
    age: Optional[int] = Field(default=None, gt=0, lt=150)
    gender: Optional[Gender] = None
    avatar_uri: Optional[str] = None
    # Add other fields admin should be able to modify, e.g., specific permissions

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Name by Admin",
                "status": "inactive",
                "is_active": False,
                "user_type": "parent",
                "phone_number": "+15551112233"
            }
        }