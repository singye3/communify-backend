# app/db/models/appearance_settings.py
from typing import Optional, Annotated 
from datetime import datetime
from beanie import Document, Link, Indexed
from pydantic import Field
from .enums import GridLayoutTypeEnum, TextSizeTypeEnum, ContrastModeTypeEnum

class AppearanceSettings(Document):
    user: Annotated[Link["User"], Indexed(unique=True)] # type: ignore
    # ---------------------------------------------
    symbol_grid_layout: GridLayoutTypeEnum = GridLayoutTypeEnum.STANDARD
    font_size: TextSizeTypeEnum = TextSizeTypeEnum.MEDIUM
    theme: ContrastModeTypeEnum = ContrastModeTypeEnum.DEFAULT
    brightness: Annotated[int, Field(ge=0, le=100)] = 50 # Integer between 0 and 100
    # ------------------------------------------------------

    tts_pitch: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5 # Float between 0.0 and 1.0
    tts_speed: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5 # Float between 0.0 and 1.0
    tts_volume: Annotated[float, Field(ge=0.0, le=1.0)] = 0.8 # Float between 0.0 and 1.0
    tts_selected_voice_id: Optional[str] = None
    tts_highlight_word: bool = True
    tts_speak_punctuation: bool = False
    selection_mode: Optional[str] = 'drag'

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings: name = "appearance_settings"
    async def before_save(self): self.updated_at = datetime.now()

from .user import User
AppearanceSettings.model_rebuild() 