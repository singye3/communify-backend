#  app/schemas/passcode.py
from typing import Optional
from pydantic import BaseModel, Field

class ParentalPasscodeVerifyRequest(BaseModel):
    passcode: str = Field(..., min_length=1, description="The parental passcode to verify.") # min_length=1 just to ensure it's not empty

class ParentalPasscodeVerifyResponse(BaseModel):
    success: bool
    message: Optional[str] = None