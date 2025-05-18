# app/db/models/appearance_settings.py

import logging
from typing import Optional, Annotated, Literal
from datetime import datetime
from beanie import Document, Link, Indexed
from pydantic import Field, model_validator
from .enums import GridLayoutTypeEnum, TextSizeTypeEnum, ContrastModeTypeEnum

logger = logging.getLogger(__name__)

class AppearanceSettings(Document):
    user: Annotated[Link["User"], Indexed(unique=True)]
    symbol_grid_layout: GridLayoutTypeEnum = Field(
        default=GridLayoutTypeEnum.STANDARD,
        description="User's preferred grid layout density.",
    )
    font_size: TextSizeTypeEnum = Field(
        default=TextSizeTypeEnum.MEDIUM, description="User's preferred base font size."
    )
    contrast_mode: ContrastModeTypeEnum = Field(
        default=ContrastModeTypeEnum.DEFAULT,
        description="Selected contrast/color theme.",
        alias="theme",
    )
    dark_mode_enabled: bool = Field(
        default=False,
        description="Explicit dark mode preference (may interact with contrast mode).",
    )
    brightness: Annotated[int, Field(ge=0, le=100)] = Field(
        default=50,
        description="In-app brightness overlay level (0=min overlay, 100=max overlay).",
    )
    tts_pitch: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.5,
        description="Text-to-Speech pitch multiplier (0.0 to 1.0 -> maps to TTS engine range).",
    )
    tts_speed: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.5,
        description="Text-to-Speech speed multiplier (0.0 to 1.0 -> maps to TTS engine range).",
    )
    tts_volume: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.8,
        description="Text-to-Speech volume multiplier (0.0 to 1.0, effectiveness varies).",
    )
    tts_selected_voice_id: Optional[str] = Field(
        default=None,
        description="Identifier (ID string) of the user's preferred TTS voice.",
    )
    tts_highlight_word: bool = Field(
        default=True,
        description="Preference for highlighting words visually during TTS playback.",
    )
    tts_speak_punctuation: bool = Field(
        default=False,
        description="Preference for having the TTS engine speak punctuation marks.",
    )
    selection_mode: Optional[Literal["drag", "longClick"]] = Field(
        default="drag",
        description="User's preferred symbol selection method ('drag' or 'longClick'). None means unset.",
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "appearance_settings"

    async def before_save(self):
        self.updated_at = datetime.now()
        if self.user and hasattr(self.user, "id"):
            logger.debug("Updating 'updated_at' for AppearanceSettings of User %s", self.user.id)
        else:
            logger.debug(
                "Updating 'updated_at' for AppearanceSettings (User link not loaded or has no ID yet)"
            )

    @model_validator(mode="after")
    def check_dark_mode_contrast_consistency(self) -> "AppearanceSettings":
        user_id_str = "Unknown"
        if self.user and hasattr(self.user, "id"):
            user_id_str = str(self.user.id)
        if (
            self.contrast_mode == ContrastModeTypeEnum.HIGH_CONTRAST_DARK
            and not self.dark_mode_enabled
        ):
            logger.warning(
                "Forcing dark_mode_enabled=True because contrast_mode is HIGH_CONTRAST_DARK for User %s",
                user_id_str,
            )
            self.dark_mode_enabled = True
        elif (
            self.contrast_mode == ContrastModeTypeEnum.HIGH_CONTRAST_LIGHT
            and self.dark_mode_enabled
        ):
            logger.warning(
                "Forcing dark_mode_enabled=False because contrast_mode is HIGH_CONTRAST_LIGHT for User %s",
                user_id_str,
            )
            self.dark_mode_enabled = False
        return self

from .user import User
AppearanceSettings.model_rebuild()