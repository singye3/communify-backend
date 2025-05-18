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
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDU5..."],
    )
    token_type: str = Field(
        default="bearer",
        description="The type of token issued (always 'bearer').",
        examples=["bearer"],
    )

    # Pydantic v2 uses model_config
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDU5NDc5MDYsInN1YiI6ImFkbWluQGNvbW11bmlmeS5hcHAifQ.AL0fhc1c2vuO3f8WSMQBdDl5fzdDoLVK9aOSeJfRwB0",
                "token_type": "bearer",
            }
        }
    }


class TokenData(BaseModel):
    """
    Schema representing the data to be extracted from the JWT access token's payload.
    If the 'sub' claim of the JWT holds the user's ID, this schema should reflect that.
    """

    user_id: Optional[str] = Field(
        default=None,
        description="The unique identifier (ID) of the user, extracted from the token's 'sub' claim.",
        examples=["6824fab73799e7675a735438"],
    )

    model_config = {
        "json_schema_extra": {"example": {"user_id": "6824fab73799e7675a735438"}}
    }
