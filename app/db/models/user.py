# app/db/models/user.py
import re
from typing import Optional, List, Annotated
from datetime import datetime, timezone
from beanie import Document, Indexed
from pydantic import Field, EmailStr, field_validator, model_validator
from .enums import UserType, UserStatus, Gender


class User(Document):
    email: Annotated[EmailStr, Indexed(unique=True)] = Field()
    name: Annotated[str, Field(min_length=1, max_length=100)] = Field()
    hashed_password: str = Field()
    user_type: UserType = Field(default=UserType.PARENT)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    age: Optional[Annotated[int, Field(ge=0, le=120)]] = Field(default=None)
    gender: Optional[Gender] = Field(default=None)
    favorite_phrases: List[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list
    )
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        indexes = [
            ("is_active", 1),
            ("user_type", 1),
        ]

    async def before_save(self):
        self.updated_at = datetime.now(timezone.utc)

    @field_validator("name", mode="before")
    @classmethod
    def strip_whitespace_name(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def check_status_consistency(self) -> "User":
        if self.is_active and self.status == UserStatus.INACTIVE:
            self.status = UserStatus.ACTIVE
        elif not self.is_active and self.status == UserStatus.ACTIVE:
            self.status = UserStatus.INACTIVE
        return self
