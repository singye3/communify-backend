# app/db/models/user.py
from typing import Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, EmailStr
from .enums import UserType, UserStatus, Gender # Import local enums

class User(Document):
    email: Indexed(EmailStr, unique=True) # type: ignore
    name: str
    hashed_password: str
    phone_number: Optional[str] = None
    user_type: UserType = UserType.PARENT # Default for general registration
    status: UserStatus = UserStatus.ACTIVE
    age: Optional[int] = None
    gender: Optional[Gender] = None
    avatar_uri: Optional[str] = None
    favorite_phrases: List[str] = Field(default_factory=list)

    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings: name = "users"
    async def before_save(self): self.updated_at = datetime.now()