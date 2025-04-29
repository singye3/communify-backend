# app/schemas/token.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class Token(BaseModel):
    """
    Schema representing the access token response provided upon successful login.
    Complies with OAuth2 standards.
    """
    access_token: str = Field(
        ...,
        description="The JWT access token string.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDU5..."]
    )
    token_type: str = Field(
        default="bearer",
        description="The type of token issued (always 'bearer').",
        examples=["bearer"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDU5NDc5MDYsInN1YiI6ImFkbWluQGNvbW11bmlmeS5hcHAifQ.AL0fhc1c2vuO3f8WSMQBdDl5fzdDoLVK9aOSeJfRwB0",
                "token_type": "bearer"
            }
        }

class TokenData(BaseModel):
    """
    Schema representing the data encoded within the JWT access token's payload.
    Currently only includes the user's email as the subject ('sub').
    """
    # Changed to Optional[EmailStr] for better type hint, depends on whether 'sub' is guaranteed
    email: Optional[EmailStr] = Field( # Or str if email format isn't strictly guaranteed in token
        default=None,
        description="The email address of the user, extracted from the token's 'sub' claim.",
        examples=["user@example.com"]
    )