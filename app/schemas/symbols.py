# app/schemas/symbols.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional


class GlobalStandardCategoriesResponse(BaseModel):
    categories: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="A dictionary where keys are category names (lowercase) "
        "and values are lists of symbol keywords.",
    )


# Payload for POST /api/v1/users/me/symbols/customized-categories/{category_name}/symbols
class UserAddSymbolPayload(BaseModel):
    keyword: str = Field(
        ..., min_length=1, description="The keyword of the symbol to add."
    )


# Represents a single symbol a user has added (used in responses)
class UserSymbolData(BaseModel):
    keyword: str

    model_config = ConfigDict(from_attributes=True)


# Response for GET /api/v1/users/me/symbols/customized-categories
class UserCustomizedCategoriesResponse(BaseModel):
    customized_symbols: Dict[str, List[UserSymbolData]] = Field(
        default_factory=dict,
        description="Symbols added by the user, grouped by category name (lowercase).",
    )


# Response for POSTing/adding a user symbol
class UserSymbolAddedResponse(BaseModel):
    message: str = "Symbol added successfully."
    category_name: str
    keyword: str
