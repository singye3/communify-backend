# app/schemas/appearance.py (New or Updated File)
from pydantic import BaseModel, Field, conint
from typing import Optional, List
from app.db.models.enums import GridLayoutTypeEnum, TextSizeTypeEnum, ContrastModeTypeEnum

# Base schema matching the AppearanceSettings model fields
class AppearanceSettingsBase(BaseModel):
    symbol_grid_layout: Optional[GridLayoutTypeEnum] = None
    font_size: Optional[TextSizeTypeEnum] = None
    theme: Optional[ContrastModeTypeEnum] = None
    brightness: Optional[conint(ge=0, le=100)] = None
    tts_pitch: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tts_speed: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tts_volume: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tts_selected_voice_id: Optional[str] = None
    tts_highlight_word: Optional[bool] = None
    tts_speak_punctuation: Optional[bool] = None
    selection_mode: Optional[str] = None # Could use Literal['drag', 'longClick', None]

# Schema for reading appearance settings
class AppearanceSettingsRead(AppearanceSettingsBase):
    id: str = Field(..., alias='_id')
    # Add user ID if needed for admin purposes
    # user_id: str

    class Config:
        from_attributes = True
        populate_by_name = True

# Schema for updating appearance settings (all fields optional)
class AppearanceSettingsUpdate(AppearanceSettingsBase):
    pass # All fields are optional from Base