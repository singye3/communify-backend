# app/schemas/auth.py
from typing import Optional
from pydantic import BaseModel, Field


# --- Schemas for /verify-parental-passcode ---
class ParentalPasscodeVerifyRequest(BaseModel):
    passcode: str = Field(
        ...,
        min_length=4,
        max_length=50,
        description="The parental passcode to verify.",
    )


class ParentalPasscodeVerifyResponse(BaseModel):
    success: bool
    message: Optional[str] = None


# --- Schemas for /set-parental-passcode ---
class ParentalPasscodeSetRequest(BaseModel):
    new_passcode: str = Field(
        ...,
        min_length=4,
        max_length=50,
        description="The new parental passcode to set.",
    )
    current_passcode: Optional[str] = Field(
        default=None,
        min_length=4,
        max_length=50,
        description="The current parental passcode, required if updating an existing one.",
    )


class ParentalPasscodeSetResponse(BaseModel):
    success: bool
    message: str


# --- Schemas for /remove-parental-passcode ---
class ParentalPasscodeRemoveRequest(BaseModel):
    current_passcode: str = Field(
        ...,
        min_length=4,
        max_length=50,
        description="The current parental passcode to authorize removal.",
    )


class ParentalPasscodeRemoveResponse(BaseModel):
    success: bool
    message: str


# --- Schemas for /has-parental-passcode ---
class HasParentalPasscodeResponse(BaseModel):
    passcode_is_set: bool
    message: Optional[str] = Field(
        default=None, description="Optional message, e.g., if settings are not found."
    )
