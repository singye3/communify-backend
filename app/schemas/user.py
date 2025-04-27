# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from .base import BaseSchema # Import if using BaseSchema

# Properties to receive via API on user creation
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8) # Ensure password meets criteria
    name: str

# Properties to receive via API on user update (Optional)
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_uri: Optional[str] = None
    # Password update should ideally be a separate endpoint

# Properties returned via API (never include hashed_password)
class UserRead(BaseSchema): # Inherit from BaseSchema if created
    # Use Pydantic v2 alias generator or Field aliases for _id
    id: str = Field(..., alias='_id') # Map _id to id
    email: EmailStr
    name: str
    avatar_uri: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
         # Ensure aliases work correctly
        populate_by_name = True # Pydantic v2
        # allow_population_by_field_name = True # Pydantic v1