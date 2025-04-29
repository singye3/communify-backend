# app/db/models/appearance_settings.py
import logging
from typing import Optional, Annotated, Literal # Import Literal for selection_mode
from datetime import datetime
from beanie import Document, Link, Indexed
from pydantic import Field, model_validator # removed unused field_validator
# Assuming enums are defined correctly in .enums
from .enums import GridLayoutTypeEnum, TextSizeTypeEnum, ContrastModeTypeEnum
# Forward reference import at the end

# Get logger instance
logger = logging.getLogger(__name__)

class AppearanceSettings(Document):
    """
    Stores user-specific appearance and interaction preferences for the application,
    linked one-to-one with a User.
    """

    # --- User Link ---
    # Ensure only one appearance settings document exists per user
    # Using Link["User"] for forward reference, resolved later
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
        alias="theme" # Allows API schemas to use 'theme' if needed for compatibility
    )
    # Added dark mode flag if needed separate from contrast
    dark_mode_enabled: bool = Field(
        default=False, # Consider if default should align with ContrastModeTypeEnum.DEFAULT
        description="Explicit dark mode preference (may interact with contrast mode)."
    )
    brightness: Annotated[int, Field(ge=0, le=100)] = Field(
        default=50, # Assuming 50% is a neutral default
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
    # Use Literal for strict validation. Optional allows it to be unset (becomes None),
    # though it defaults to 'drag' if not provided.
    selection_mode: Optional[Literal['drag', 'longClick']] = Field(
        default='drag',
        description="User's preferred symbol selection method ('drag' or 'longClick'). None means unset."
    )

    # --- Timestamps ---
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # --- Beanie Settings ---
    class Settings:
        name = "appearance_settings" # MongoDB collection name

    # --- Hooks ---
    # Use @Before(Insert, Replace, Save) in newer Beanie versions?
    # Or keep before_save for compatibility.
    async def before_save(self):
        """Automatically update 'updated_at' timestamp before saving."""
        self.updated_at = datetime.now()
        # Accessing self.user.id here is generally fine, Beanie handles links.
        # The # type: ignore is often needed for static analyzers with Links.
        if self.user and hasattr(self.user, 'id'):
            logger.debug("Updating 'updated_at' for AppearanceSettings of User %s", self.user.id) # type: ignore
        else:
             logger.debug("Updating 'updated_at' for AppearanceSettings (User link not loaded or has no ID yet)")


    # --- Model Validators ---
    @model_validator(mode='after')
    def check_dark_mode_contrast_consistency(self) -> 'AppearanceSettings':
        """
        Ensures dark_mode_enabled aligns with specific high-contrast modes,
        preventing contradictory states if required by frontend theme logic.
        Modifies dark_mode_enabled directly and logs a warning.
        """
        user_id_str = "Unknown"
        if self.user and hasattr(self.user, 'id'):
             user_id_str = str(self.user.id) # type: ignore

        if self.contrast_mode == ContrastModeTypeEnum.HIGH_CONTRAST_DARK and not self.dark_mode_enabled:
            logger.warning(
                "Forcing dark_mode_enabled=True because contrast_mode is HIGH_CONTRAST_DARK for User %s",
                user_id_str
            )
            self.dark_mode_enabled = True
        # Optional: Decide if HIGH_CONTRAST_LIGHT should force dark_mode_enabled=False
        elif self.contrast_mode == ContrastModeTypeEnum.HIGH_CONTRAST_LIGHT and self.dark_mode_enabled:
             logger.warning(
                "Forcing dark_mode_enabled=False because contrast_mode is HIGH_CONTRAST_LIGHT for User %s",
                user_id_str
            )
             self.dark_mode_enabled = False
        # Consider adding a case for `ContrastModeTypeEnum.DEFAULT` if it should imply dark/light mode
        # elif self.contrast_mode == ContrastModeTypeEnum.DEFAULT and self.dark_mode_enabled:
             # logger.warning(...)
             # self.dark_mode_enabled = False # If default theme is always light

        return self


# --- Forward Reference Resolution ---
# Import the linked model class AFTER AppearanceSettings is defined
from .user import User
# Rebuild the model to resolve the ForwardRef ("User") in the Link
AppearanceSettings.model_rebuild()