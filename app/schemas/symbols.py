# app/schemas/symbols.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional

# --- Schemas for Global Standard Categories ---

# Response for GET /api/v1/symbols/standard-categories
# This is already implicitly handled by returning Dict[str, List[str]]
# but defining it can be good for documentation or if it becomes more complex.
class GlobalStandardCategoriesResponse(BaseModel):
    categories: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="A dictionary where keys are category names (lowercase) "
                    "and values are lists of symbol keywords."
    )
    # You could add metadata here if needed, like a version or last_updated timestamp.

    # Example if you directly return the dict without nesting under 'categories':
    # __root__: Dict[str, List[str]] # For Pydantic v1 root models
    # For Pydantic v2, if the endpoint directly returns Dict[str, List[str]],
    # then `response_model=Dict[str, List[str]]` in the endpoint is sufficient.


# --- Schemas for User-Specific Symbol Customizations ---

# Payload for POST /api/v1/users/me/symbols/customized-categories/{category_name}/symbols
class UserAddSymbolPayload(BaseModel):
    keyword: str = Field(..., min_length=1, description="The keyword of the symbol to add.")
    # image_uri: Optional[str] = Field(default=None, description="Optional image URI for the symbol.")
    # Any other data the user can provide when adding a symbol

# Represents a single symbol a user has added (used in responses)
class UserSymbolData(BaseModel):
    keyword: str
    # image_uri: Optional[str] = None
    # id: Optional[str] = None # ID of the UserCategorySymbol document if needed in response

    model_config = ConfigDict(from_attributes=True)


# Response for GET /api/v1/users/me/symbols/customized-categories
class UserCustomizedCategoriesResponse(BaseModel):
    customized_symbols: Dict[str, List[UserSymbolData]] = Field(
        default_factory=dict,
        description="Symbols added by the user, grouped by category name (lowercase)."
    )

# Response for POSTing/adding a user symbol
class UserSymbolAddedResponse(BaseModel):
    message: str = "Symbol added successfully."
    category_name: str
    keyword: str
    # id: str # ID of the created UserCategorySymbol document

# (Optional) Payload for DELETING a user symbol
# class UserDeleteSymbolPayload(BaseModel):
#     keyword: str # Or you might use the UserCategorySymbol document ID if you return it