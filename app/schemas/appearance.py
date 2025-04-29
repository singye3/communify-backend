# app/schemas/appearance.py
from pydantic import BaseModel, Field, EmailStr, field_validator, conint # Import conint if still needed, though Annotated is preferred
from typing import Optional, List, Annotated, Literal # Import Annotated and Literal
from app.db.models.enums import GridLayoutTypeEnum, TextSizeTypeEnum, ContrastModeTypeEnum

# --- Base Schema ---
# Defines all possible fields related to appearance settings.
# Used as a base for Update (all optional) and Read (adds id).
class AppearanceSettingsBase(BaseModel):
    symbol_grid_layout: Optional[GridLayoutTypeEnum] = Field(
        default=None,
        description="Preferred grid layout density for symbol display."
    )
    font_size: Optional[TextSizeTypeEnum] = Field(
        default=None,
        description="Preferred base font size for the application."
    )
    # 'theme' now maps to contrast mode in our model
    contrast_mode: Optional[ContrastModeTypeEnum] = Field( # Renamed for clarity
        default=None,
        alias="theme", # Allow 'theme' in request/response for compatibility if needed
        validation_alias="theme", # Allow receiving 'theme' as input
        description="Selected contrast/color theme."
    )
    # Use Annotated for brightness validation (preferred over conint)
    brightness: Optional[Annotated[int, Field(ge=0, le=100)]] = Field(
        default=None,
        description="In-app brightness overlay level (0-100)."
    )
    # Use Annotated for float constraints
    tts_pitch: Optional[Annotated[float, Field(ge=0.0, le=1.0)]] = Field(
        default=None,
        description="Text-to-Speech pitch setting (0.0 to 1.0)."
    )
    tts_speed: Optional[Annotated[float, Field(ge=0.0, le=1.0)]] = Field(
        default=None,
        description="Text-to-Speech speed setting (0.0 to 1.0)."
    )
    tts_volume: Optional[Annotated[float, Field(ge=0.0, le=1.0)]] = Field(
        default=None,
        description="Text-to-Speech volume setting (0.0 to 1.0)."
    )
    tts_selected_voice_id: Optional[str] = Field(
        default=None,
        description="Identifier for the selected TTS voice."
    )
    tts_highlight_word: Optional[bool] = Field(
        default=None,
        description="Whether to highlight words as they are spoken."
    )
    tts_speak_punctuation: Optional[bool] = Field(
        default=None,
        description="Whether the TTS engine should speak punctuation marks."
    )
    # Use Literal for fixed string options
    selection_mode: Optional[Literal['drag', 'longClick']] = Field(
        default=None,
        description="Preferred method for selecting symbols ('drag' or 'longClick')."
    )
    # Add darkModeEnabled if you want to control it separately from contrast_mode
    dark_mode_enabled: Optional[bool] = Field(
         default=None,
         description="Explicitly enable/disable dark mode (can override theme/contrast)."
    )

    class Config:
        # Enable ORM mode (or from_attributes in Pydantic v2)
        # to allow creating schema instances from model objects
        from_attributes = True
        # Allow using field names OR aliases during model creation/parsing
        populate_by_name = True
        # Define examples for Swagger UI/OpenAPI documentation
        json_schema_extra = {
            "example": {
                "symbol_grid_layout": "standard",
                "font_size": "medium",
                "contrast_mode": "default", # Or use "theme": "default" if using alias
                "brightness": 80,
                "tts_pitch": 0.5,
                "tts_speed": 0.6,
                "tts_volume": 0.9,
                "tts_selected_voice_id": "com.apple.voice.compact.en-US.Samantha",
                "tts_highlight_word": True,
                "tts_speak_punctuation": False,
                "selection_mode": "drag",
                "dark_mode_enabled": False,
            }
        }


# --- Schema for Reading Data ---
# Inherits all fields from Base and adds the database ID.
class AppearanceSettingsRead(AppearanceSettingsBase):
    id: str = Field(..., alias='_id', description="Unique identifier for the settings document.")
    # Optionally include user identifier if needed (e.g., for admin views)
    # user_id: str = Field(..., description="ID of the user these settings belong to.")

    class Config:
        # Ensure ORM mode and alias population are enabled for reading
        from_attributes = True
        populate_by_name = True
        # Example for Read schema
        json_schema_extra = {
            "example": {
                "id": "6811a5b...",
                "symbol_grid_layout": "standard",
                "font_size": "medium",
                "contrast_mode": "default",
                "brightness": 80,
                "tts_pitch": 0.5,
                "tts_speed": 0.6,
                "tts_volume": 0.9,
                "tts_selected_voice_id": "com.apple.voice.compact.en-US.Samantha",
                "tts_highlight_word": True,
                "tts_speak_punctuation": False,
                "selection_mode": "drag",
                "dark_mode_enabled": False,
            }
        }


# --- Schema for Updating Data ---
# Inherits all fields from Base. In Pydantic, fields inherited into a model
# without a new default value automatically become optional for input.
# This schema expects a PATCH-like behavior where only provided fields are updated.
class AppearanceSettingsUpdate(AppearanceSettingsBase):
    # No additional fields needed here. By inheriting from Base without overriding
    # defaults, all fields become optional inputs for the update operation.
     class Config:
        # Example for Update schema (showing only a few fields being updated)
        json_schema_extra = {
            "example": {
                "font_size": "large",
                "tts_speed": 0.7,
                "contrast_mode": "high-contrast-dark"
            }
        }