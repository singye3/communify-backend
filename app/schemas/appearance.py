# app/schemas/appearance.py
from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    field_validator,
    conint,
)
from typing import Optional, List, Annotated, Literal
from app.db.models.enums import (
    GridLayoutTypeEnum,
    TextSizeTypeEnum,
    ContrastModeTypeEnum,
)


class AppearanceSettingsBase(BaseModel):
    symbol_grid_layout: Optional[GridLayoutTypeEnum] = Field(
        default=None, description="Preferred grid layout density for symbol display."
    )
    font_size: Optional[TextSizeTypeEnum] = Field(
        default=None, description="Preferred base font size for the application."
    )
    contrast_mode: Optional[ContrastModeTypeEnum] = Field(
        default=None,
        alias="theme",
        validation_alias="theme",
        description="Selected contrast/color theme.",
    )
    brightness: Optional[Annotated[int, Field(ge=0, le=100)]] = Field(
        default=None, description="In-app brightness overlay level (0-100)."
    )
    tts_pitch: Optional[Annotated[float, Field(ge=0.0, le=1.0)]] = Field(
        default=None, description="Text-to-Speech pitch setting (0.0 to 1.0)."
    )
    tts_speed: Optional[Annotated[float, Field(ge=0.0, le=1.0)]] = Field(
        default=None, description="Text-to-Speech speed setting (0.0 to 1.0)."
    )
    tts_volume: Optional[Annotated[float, Field(ge=0.0, le=1.0)]] = Field(
        default=None, description="Text-to-Speech volume setting (0.0 to 1.0)."
    )
    tts_selected_voice_id: Optional[str] = Field(
        default=None, description="Identifier for the selected TTS voice."
    )
    tts_highlight_word: Optional[bool] = Field(
        default=None, description="Whether to highlight words as they are spoken."
    )
    tts_speak_punctuation: Optional[bool] = Field(
        default=None,
        description="Whether the TTS engine should speak punctuation marks.",
    )
    selection_mode: Optional[Literal["drag", "longClick"]] = Field(
        default=None,
        description="Preferred method for selecting symbols ('drag' or 'longClick').",
    )
    dark_mode_enabled: Optional[bool] = Field(
        default=None,
        description="Explicitly enable/disable dark mode (can override theme/contrast).",
    )

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "symbol_grid_layout": "standard",
                "font_size": "medium",
                "theme": "default",
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


class AppearanceSettingsRead(AppearanceSettingsBase):
    id: str = Field(
        ..., alias="_id", description="Unique identifier for the settings document."
    )

    class Config:
        from_attributes = True
        populate_by_name = True
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


class AppearanceSettingsUpdate(AppearanceSettingsBase):
    class Config:
        json_schema_extra = {
            "example": {
                "font_size": "large",
                "tts_speed": 0.7,
                "theme": "high-contrast-dark",
            }
        }
