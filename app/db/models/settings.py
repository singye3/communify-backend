# app/db/models/settings.py
import logging # Added logging
from typing import Optional, List, Annotated, Any
from datetime import datetime, time
from beanie import Document, Link, Indexed
from pydantic import Field, EmailStr, field_validator, model_validator # Removed ValidationError as it wasn't explicitly used for raising
# Assuming enums are defined correctly in .enums
from .enums import AsdLevel, DayOfWeek
# Forward reference import at the end

# Get logger instance
logger = logging.getLogger(__name__)

class ParentalSettings(Document):
    # Link to the User, ensuring one settings doc per user
    user: Annotated[Link["User"], Indexed(unique=True)] # type: ignore

    # --- Content Blocking ---
    block_violence: bool = Field(
        default=False,
        description="Block content categorized as violent."
    )
    block_inappropriate: bool = Field(
        default=False,
        description="Block content categorized as inappropriate for children."
    )

    # --- Time Limits & Scheduling ---
    daily_limit_hours: Optional[str] = Field(
        default=None,
        pattern=r"^(?:[0-9]|1[0-9]|2[0-4])?$", # Allows empty string or 0-24
        description="Daily screen time limit in hours (0-24). Null or empty means no limit."
    )
    downtime_enabled: bool = Field(
        default=False,
        description="Enable scheduled downtime periods."
    )
    downtime_days: List[DayOfWeek] = Field(
        default_factory=list,
        description="List of days (Mon-Sun) when downtime is active."
    )
    downtime_start: str = Field(
        default="21:00",
        pattern=r"^[0-2][0-9]:[0-5][0-9]$", # Enforces HH:MM format
        description="Downtime start time in HH:MM (24-hour) format."
    )
    downtime_end: str = Field(
        default="07:00",
        pattern=r"^[0-2][0-9]:[0-5][0-9]$", # Enforces HH:MM format
        description="Downtime end time in HH:MM (24-hour) format."
    )

    # --- Access & Notifications ---
    require_passcode: bool = Field(
        default=False,
        description="Require parental passcode for changing settings or exiting restricted modes."
    )
    notify_emails: List[EmailStr] = Field(
        default_factory=list,
        description="List of email addresses for notifications/reports."
    )

    # --- Other Preferences ---
    asd_level: Optional[AsdLevel] = Field(
        default=None,
        description="Selected Autism Spectrum Disorder support level."
    )
    data_sharing_preference: bool = Field(
        default=False,
        description="User preference for anonymous data sharing."
    )

    # --- Timestamps ---
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # --- Beanie Settings ---
    class Settings:
        name = "parental_settings" # MongoDB collection name

    # --- Hooks ---
    async def before_save(self):
        """Automatically update 'updated_at' before saving."""
        self.updated_at = datetime.now()
        # Optional: Add logging like in AppearanceSettings if desired
        # if self.user and hasattr(self.user, 'id'):
        #     logger.debug("Updating 'updated_at' for ParentalSettings of User %s", self.user.id) # type: ignore


    # --- Field Validators ---
    @field_validator('downtime_days', mode='before')
    @classmethod
    def sort_and_validate_downtime_days(cls, v: Any) -> List[DayOfWeek]:
        """Sorts, validates, and de-duplicates the list of downtime days upon setting/updating."""
        if not isinstance(v, list):
             # Return early or raise error if input is not a list
             raise ValueError('downtime_days must be provided as a list')
        try:
            # Define the canonical order for sorting
            day_order: List[DayOfWeek] = [
                DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED,
                DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN
            ]
            # Validate each item against DayOfWeek enum, use set for deduplication
            valid_days_enum = {DayOfWeek(item) for item in v if item in DayOfWeek.__members__.values()}
            # Sort the unique, valid days based on the canonical order
            return sorted(list(valid_days_enum), key=lambda day: day_order.index(day))
        except ValueError as e:
            # Catch errors from invalid DayOfWeek values
            invalid_items = [item for item in v if item not in DayOfWeek.__members__.values()]
            raise ValueError(f"Invalid day(s) found in downtime_days: {invalid_items}. Must be one of {', '.join(d.value for d in DayOfWeek)}") from e
        except TypeError as e:
             # Catch errors if items in the list are not strings/suitable for enum conversion
             raise ValueError(f"Invalid type found in downtime_days list: {e}") from e

    @field_validator('daily_limit_hours', mode='before')
    @classmethod
    def validate_optional_hour_string(cls, v: Any) -> Optional[str]:
        """Allows None or empty string (returns None), otherwise validates numeric string range 0-24."""
        if v is None or v == "":
            return None # Treat empty string same as None (no limit)
        try:
            # Ensure it's a string consisting only of digits
            if not isinstance(v, str) or not v.isdigit():
                 raise ValueError("Limit must be a whole number string (e.g., '2', '10') if provided.")
            hour = int(v)
            # Validate the numeric range
            if not (0 <= hour <= 24):
                raise ValueError("Daily limit hours must be between 0 and 24.")
            # Return the validated string representation
            return str(hour)
        except (ValueError, TypeError) as e:
             # Catch potential int conversion errors or validation errors
             raise ValueError(f"Invalid daily limit hours value '{v}': {e}") from e


    # --- Model Validators ---
    @model_validator(mode='after')
    def check_downtime_enabled_dependencies(self):
        """
        Ensures that if downtime is enabled, at least one day must be selected.
        (Time format is already validated by Field patterns).
        """
        if self.downtime_enabled and not self.downtime_days:
            # Raise error if downtime is on but no days are chosen
            raise ValueError('If downtime is enabled, at least one active day (downtime_days) must be selected.')
        return self

    @model_validator(mode='after')
    def check_passcode_requirement(self):
        """
        Placeholder validator. If require_passcode is True, the actual check
        to ensure a passcode IS SET would likely need to happen in the API endpoint
        logic before saving, as this model cannot access external storage like Keychain.
        """
        if self.require_passcode:
            # Log a note or perform any model-internal checks if needed
            logger.info("ParentalSettings saved with require_passcode=True. Ensure passcode exists externally.")
            pass # No direct action possible here, logic belongs in service/endpoint layer
        return self


# --- Forward Reference Resolution ---
# Import the linked model class AFTER ParentalSettings is defined
from .user import User
# Rebuild the model to resolve the ForwardRef ("User") in the Link
ParentalSettings.model_rebuild()