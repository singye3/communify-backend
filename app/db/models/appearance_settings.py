# app/db/models/appearance_settings.py
import logging
from typing import Optional, Annotated, Literal # Import Literal for selection_mode
from datetime import datetime
from beanie import Document, Link, Indexed
from pydantic import Field, field_validator, model_validator
from .enums import GridLayoutTypeEnum, TextSizeTypeEnum, ContrastModeTypeEnum

# Get logger instance
logger = logging.getLogger(__name__)

class AppearanceSettings(Document):
    """
    Stores user-specific appearance and interaction preferences for the application,
    linked one-to-one with a User.
    """

    # --- User Link ---
    # Ensure only one appearance settings document exists per user
    user: Annotated[Link["User"], Indexed(unique=True)] # type: ignore

    # --- Display/Grid Settings ---
    symbol_grid_layout: GridLayoutTypeEnum = Field(
        default=GridLayoutTypeEnum.STANDARD,
        description="User's preferred grid layout density."
    )

    # --- Appearance Settings ---
    font_size: TextSizeTypeEnum = Field(
        default=TextSizeTypeEnum.MEDIUM,
        description="User's preferred base font size."
    )
    # Renamed 'theme' to 'contrast_mode' internally for clarity, maps to ContrastModeTypeEnum
    contrast_mode: ContrastModeTypeEnum = Field(
        default=ContrastModeTypeEnum.DEFAULT,
        description="Selected contrast/color theme.",
        alias="theme" # Allow 'theme' in API schemas if needed for frontend compatibility
    )
    # Added dark mode flag if needed separate from contrast
    dark_mode_enabled: bool = Field(
        default=False, # Or derive from system Appearance API on first load?
        description="Explicit dark mode preference (may interact with contrast mode)."
    )
    brightness: Annotated[int, Field(ge=0, le=100)] = Field(
        default=50,
        description="In-app brightness overlay level (0=min overlay, 100=max overlay)."
    )

    # --- TTS Preferences ---
    tts_pitch: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.5,
        description="Text-to-Speech pitch multiplier (0.0 to 1.0 -> maps to TTS engine range)."
    )
    tts_speed: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.5,
        description="Text-to-Speech speed multiplier (0.0 to 1.0 -> maps to TTS engine range)."
    )
    tts_volume: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.8,
        description="Text-to-Speech volume multiplier (0.0 to 1.0, effectiveness varies)."
    )
    tts_selected_voice_id: Optional[str] = Field(
        default=None,
        description="Identifier (ID string) of the user's preferred TTS voice."
    )

    # --- Interaction / Behavior Settings ---
    tts_highlight_word: bool = Field(
        default=True,
        description="Preference for highlighting words visually during TTS playback."
    )
    tts_speak_punctuation: bool = Field(
        default=False,
        description="Preference for having the TTS engine speak punctuation marks."
    )
    # Use Literal for strict validation of selection_mode values
    selection_mode: Optional[Literal['drag', 'longClick']] = Field(
        default='drag', # Default to drag
        description="User's preferred symbol selection method ('drag' or 'longClick')."
    )

    # --- Timestamps ---
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # --- Beanie Settings ---
    class Settings:
        name = "appearance_settings" # MongoDB collection name

    # --- Hooks ---
    async def before_save(self):
        """Automatically update 'updated_at' timestamp before saving."""
        self.updated_at = datetime.now()
        logger.debug("Updating 'updated_at' for AppearanceSettings of User %s", self.user.id) # type: ignore

    # --- Model Validators ---
    @model_validator(mode='after')
    def check_dark_mode_contrast_consistency(self) -> 'AppearanceSettings':
        """
        Ensures dark_mode_enabled aligns with high-contrast-dark theme,
        preventing contradictory states if needed by the frontend theme logic.
        """
        if self.contrast_mode == ContrastModeTypeEnum.HIGH_CONTRAST_DARK and not self.dark_mode_enabled:
            logger.warning(
                "Setting dark_mode_enabled=True because contrast_mode is HIGH_CONTRAST_DARK for User %s",
                self.user.id # type: ignore
            )
            self.dark_mode_enabled = True
        elif self.contrast_mode == ContrastModeTypeEnum.HIGH_CONTRAST_LIGHT and self.dark_mode_enabled:
             logger.warning(
                "Setting dark_mode_enabled=False because contrast_mode is HIGH_CONTRAST_LIGHT for User %s",
                self.user.id # type: ignore
            )
             self.dark_mode_enabled = False
        return self


# --- Forward Reference Resolution ---
from .user import User 
AppearanceSettings.model_rebuild()