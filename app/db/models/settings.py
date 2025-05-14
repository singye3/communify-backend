# app/db/models/settings.py
import logging
from typing import Optional, List, Annotated, Any
from datetime import datetime # time import removed as not directly used here
from beanie import Document, Link, Indexed
from pydantic import Field, EmailStr, field_validator, model_validator

# Assuming enums are defined correctly in .enums
from .enums import AsdLevel, DayOfWeek # Ensure these enums are correctly defined
# Forward reference import for User will be at the end

logger = logging.getLogger(__name__)

class ParentalSettings(Document):
    # Link to the User, ensuring one settings doc per user.
    # user_id field is often implicitly created by Beanie for Links if not explicitly named 'user'.
    # If you want the field in MongoDB to be 'user_id', use:
    # user: Link["User"] = Field(..., alias="user_id")
    # For direct linking by Beanie's default behavior (field name 'user' storing Link[User]):
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
        default=None, # None means no limit
        pattern=r"^(?:[0-9]|1[0-9]|2[0-4])?$", # Allows empty string (which validator converts to None) or 0-24
        description="Daily screen time limit in hours (0-24). Null or empty means no limit."
    )
    downtime_enabled: bool = Field(
        default=False,
        description="Enable scheduled downtime periods."
    )
    # Stores DayOfWeek enum members in the DB (Beanie typically stores their .value - string)
    downtime_days: List[DayOfWeek] = Field(
        default_factory=list,
        description="List of days (Mon-Sun) when downtime is active."
    )
    downtime_start: str = Field(
        default="21:00",
        pattern=r"^(?:[01]\d|2[0-3]):(?:[0-5]\d)$", # Stricter HH:MM format
        description="Downtime start time in HH:MM (24-hour) format."
    )
    downtime_end: str = Field(
        default="07:00",
        pattern=r"^(?:[01]\d|2[0-3]):(?:[0-5]\d)$", # Stricter HH:MM format
        description="Downtime end time in HH:MM (24-hour) format."
    )

    # --- Access & Notifications ---
    require_passcode: bool = Field(
        default=False,
        description="Require parental passcode for changing settings or exiting restricted modes."
    )
    hashed_parental_passcode: Optional[str] = Field(None, description="Stores the hashed parental passcode.")
    notify_emails: List[EmailStr] = Field(
        default_factory=list,
        description="List of email addresses for notifications/reports."
    )

    # --- Other Preferences ---
    # Stores AsdLevel enum member in the DB (Beanie typically stores its .value - string, or None)
    asd_level: Optional[AsdLevel] = Field(
        default=None, # None represents "no specific needs" or not set
        description="Selected Autism Spectrum Disorder support level."
    )
    data_sharing_preference: bool = Field(
        default=False,
        description="User preference for anonymous data sharing."
    )

    # --- Timestamps ---
    created_at: datetime = Field(default_factory=datetime.utcnow) # Use utcnow for consistency
    updated_at: datetime = Field(default_factory=datetime.utcnow) # Use utcnow

    # --- Beanie Settings ---
    class Settings:
        name = "parental_settings"
        # Example: keep_nulls = False # if you don't want to store fields that are None

    # --- Hooks ---
    async def before_save(self, *args: Any, **kwargs: Any) -> None: # Added *args, **kwargs for Beanie hook signature
        """Automatically update 'updated_at' before saving."""
        self.updated_at = datetime.utcnow()
        # Optional: Log user ID if available and if it's a fetched document
        # Beanie link might not be fetched by default, so self.user.id might cause another DB call or error.
        # if self.user and self.user.id: # Check if link is fetched and has id
        #    logger.debug(f"Updating 'updated_at' for ParentalSettings of User {self.user.id}")


    # --- Field Validators ---
    @field_validator('downtime_days', mode='before')
    @classmethod
    def sort_and_validate_downtime_days(cls, v: Any) -> List[DayOfWeek]:
        if not isinstance(v, list):
             raise ValueError('downtime_days must be a list.')
        
        # Define the canonical order for sorting
        day_order_map: Dict[DayOfWeek, int] = {
            DayOfWeek.MON: 0, DayOfWeek.TUE: 1, DayOfWeek.WED: 2,
            DayOfWeek.THU: 3, DayOfWeek.FRI: 4, DayOfWeek.SAT: 5, DayOfWeek.SUN: 6
        }
        
        valid_days_enum_set = set()
        invalid_items = []
        for item in v:
            try:
                # Attempt to convert to DayOfWeek enum member
                day_enum_member = DayOfWeek(item) # Pydantic v2 handles enum conversion from value
                valid_days_enum_set.add(day_enum_member)
            except ValueError: # If item is not a valid DayOfWeek value
                invalid_items.append(item)
        
        if invalid_items:
            allowed_values = ", ".join(d.value for d in DayOfWeek)
            raise ValueError(f"Invalid day(s) in downtime_days: {invalid_items}. Allowed: {allowed_values}.")
            
        # Sort the unique, valid days based on the canonical order
        return sorted(list(valid_days_enum_set), key=lambda day_enum: day_order_map[day_enum])

    @field_validator('daily_limit_hours', mode='before')
    @classmethod
    def validate_optional_hour_string(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None # Consistent representation for no limit
        
        if not isinstance(v, str):
            # If it's an int/float, try to convert, else raise.
            if isinstance(v, (int, float)) and 0 <= v <= 24:
                return str(int(v)) # Convert valid numbers to string
            raise ValueError("Daily limit hours must be a string representing a number.")

        if not v.isdigit(): # Check after ensuring it's a string
             raise ValueError("Limit must be a whole number string (e.g., '2', '10') if provided.")
        
        try:
            hour = int(v)
            if not (0 <= hour <= 24): # Python's range includes start, excludes end.
                raise ValueError("Daily limit hours must be between 0 and 24 inclusive.")
            return str(hour) # Return the validated string
        except ValueError as e: # Catch int conversion error or the error raised above
             raise ValueError(f"Invalid daily limit hours value '{v}': {e}")


    # --- Model Validators ---
    @model_validator(mode='after')
    def check_downtime_enabled_dependencies(self) -> "ParentalSettings": # Return self
        """
        Ensures that if downtime is enabled, at least one day must be selected.
        (Time format is already validated by Field patterns).
        """
        if self.downtime_enabled and not self.downtime_days:
            raise ValueError('If downtime is enabled, at least one active day (downtime_days) must be selected.')
        return self

    @model_validator(mode='after')
    def check_passcode_requirement(self) -> "ParentalSettings": # Return self
        """
        Placeholder for model-internal checks related to passcode.
        Actual enforcement of passcode presence happens in API endpoints.
        """
        if self.require_passcode:
            logger.debug("ParentalSettings model indicates require_passcode=True. External check for passcode existence is necessary.")
        return self


# --- Forward Reference Resolution ---
from .user import User # Ensure this import path is correct
ParentalSettings.model_rebuild(force=True) # Pydantic v2 uses model_rebuild