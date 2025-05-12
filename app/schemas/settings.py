# app/schemas/settings.py
import logging
from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    field_validator,
    model_validator,
    ConfigDict
)
from typing import Optional, List, Annotated, Any # Removed Dict as it's not directly used in schema defs

from app.db.models.enums import AsdLevel, DayOfWeek # Ensure these are correctly imported

# --- Constants ---
DAY_ORDER: List[DayOfWeek] = [
    DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED,
    DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN
]
TIME_PATTERN = r"^[0-2][0-9]:[0-5][0-9]$" # HH:MM format
HOURS_PATTERN = r"^(?:[0-9]|1[0-9]|2[0-3])?$" # 0-23 hours, or empty string for no limit.
                                            # Changed 24 to 23 for hours in a day. Or allow "24" if that means "full day"
                                            # If empty string means no limit, pattern should allow it or handle in validator

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Base Schema (Defines all available Parental Settings fields and their validation) ---
class ParentalSettingsFields(BaseModel):
    """
    Contains all individual fields for parental settings.
    Used as the structure for the 'value' object in PATCH requests
    and as the base for Read/Create operations.
    All fields are optional here because for PATCH, any subset can be provided.
    Defaults are defined in ParentalSettingsBase for creation.
    """
    block_violence: Optional[bool] = Field(None, description="Block content categorized as violent.")
    block_inappropriate: Optional[bool] = Field(None, description="Block content categorized as inappropriate for children.")
    daily_limit_hours: Optional[Annotated[str, Field(pattern=HOURS_PATTERN)]] = Field(
        None, # For PATCH, default is None; actual default on creation is in ParentalSettingsBase
        description="Daily screen time usage limit in hours (0-23). Null or empty string means no limit.",
        examples=["", "2", "10", "23", None]
    )
    asd_level: Optional[AsdLevel] = Field(None, description="Selected Autism Spectrum Disorder support level.")
    downtime_enabled: Optional[bool] = Field(None, description="Enable scheduled downtime periods.")
    downtime_days: Optional[List[DayOfWeek]] = Field(None, description="Days when downtime is active. Sorted automatically.")
    downtime_start: Optional[Annotated[str, Field(pattern=TIME_PATTERN)]] = Field(
        None, description="Downtime start time in HH:MM (24-hour).", examples=["09:00", "22:30"]
    )
    downtime_end: Optional[Annotated[str, Field(pattern=TIME_PATTERN)]] = Field(
        None, description="Downtime end time in HH:MM (24-hour).", examples=["17:00", "06:00"]
    )
    require_passcode: Optional[bool] = Field(None, description="Require passcode for changing settings.")
    notify_emails: Optional[List[EmailStr]] = Field(None, description="Emails for usage reports/notifications.")
    data_sharing_preference: Optional[bool] = Field(None, description="Preference for anonymous data sharing.")

    # --- Field Validators specific to the values themselves ---
    @field_validator('downtime_days', mode='before')
    @classmethod
    def validate_and_sort_downtime_days(cls, v: Optional[List[Any]]) -> Optional[List[DayOfWeek]]:
        if v is None: # Allow None for PATCH
            return None
        if not isinstance(v, list):
            raise ValueError("downtime_days must be a list (e.g., ['Mon', 'Fri']) or null.")

        valid_days_enum: set[DayOfWeek] = set()
        invalid_days: list[str] = []
        for item in v:
            try:
                day_enum = DayOfWeek(str(item)) # Ensure item is treated as string for enum conversion
                valid_days_enum.add(day_enum)
            except ValueError:
                invalid_days.append(str(item))

        if invalid_days:
            valid_options = ", ".join(d.value for d in DayOfWeek)
            raise ValueError(
                f"Invalid day(s) in downtime_days: {', '.join(invalid_days)}. Allowed: {valid_options}."
            )
        return sorted(list(valid_days_enum), key=lambda day: DAY_ORDER.index(day)) if valid_days_enum else []

    # Model validator for time logic, applied when relevant fields are present
    @model_validator(mode='after')
    def check_downtime_times_if_present(self) -> 'ParentalSettingsFields':
        # This validator runs on the fields provided in a PATCH 'value' object.
        # It should only validate if both start and end times are provided in the PATCH.
        if self.downtime_start is not None and self.downtime_end is not None:
            try:
                start_h, start_m = map(int, self.downtime_start.split(':'))
                end_h, end_m = map(int, self.downtime_end.split(':'))
                if (start_h * 60 + start_m) == (end_h * 60 + end_m):
                    error_detail = "Downtime start and end times cannot be the same."
                    # Pydantic v2 expects a PydanticCustomError or similar for model validation errors
                    # For simplicity, we'll raise ValueError that endpoint can catch or rely on FastAPI to wrap.
                    # A more robust way is to use ErrorWrappers if this is within a broader validation flow.
                    raise ValueError(error_detail) # Simpler, will be wrapped by FastAPI
            except ValueError as e: # Catch specific error from split/map or our custom raise
                 # If it's our custom error, re-raise it
                if "cannot be the same" in str(e):
                    # For field-specific errors in model_validator, you'd typically add errors
                    # to a list and raise a single ValidationError at the end, or use Pydantic's
                    # mechanisms for reporting multiple errors. Here, raising ValueError is simpler.
                    raise ValueError({'downtime_start': str(e), 'downtime_end': str(e)})
                logger.warning(f"Invalid time format in downtime_start/end: {self.downtime_start}, {self.downtime_end}. Error: {e}")
                raise ValueError({'downtime_start': 'Invalid time format.', 'downtime_end': 'Invalid time format.'})
            except Exception as e: # Catch any other unexpected error
                logger.exception(f"Unexpected error validating downtime times: {e}")
                raise ValueError("Internal error during downtime time validation.")
        return self

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True, # Good for models representing data state
        extra='ignore', # Ignore extra fields not defined in this schema
        use_enum_values=True, # For PATCH, client usually sends string values for enums
    )


class ParentalSettingsBase(ParentalSettingsFields):
    """
    Base schema for parental settings, establishing default values for creation.
    Inherits all fields and their validators from ParentalSettingsFields.
    """
    # Override fields from ParentalSettingsFields to provide creation defaults
    block_violence: bool = Field(False, description="Block content categorized as violent.")
    block_inappropriate: bool = Field(False, description="Block content categorized as inappropriate for children.")
    daily_limit_hours: Optional[Annotated[str, Field(pattern=HOURS_PATTERN)]] = Field(
        None, description="Daily screen time limit (0-23 hours). Null/empty means no limit."
    )
    asd_level: Optional[AsdLevel] = Field(AsdLevel.NO_ASD, description="Default ASD support level.") # Default for creation
    downtime_enabled: bool = Field(False, description="Enable scheduled downtime periods.")
    downtime_days: List[DayOfWeek] = Field(default_factory=list, description="Days for downtime.")
    downtime_start: Annotated[str, Field(pattern=TIME_PATTERN)] = Field("21:00", description="Default downtime start.")
    downtime_end: Annotated[str, Field(pattern=TIME_PATTERN)] = Field("07:00", description="Default downtime end.")
    require_passcode: bool = Field(False, description="Require passcode for settings changes.")
    notify_emails: List[EmailStr] = Field(default_factory=list, description="Emails for notifications.")
    data_sharing_preference: bool = Field(False, description="Preference for anonymous data sharing.")

    # Model validator specific to creation/full validation context
    @model_validator(mode='after')
    def check_downtime_config_on_create(self) -> 'ParentalSettingsBase':
        if self.downtime_enabled and not self.downtime_days:
            # For model validators, it's better to raise errors that Pydantic can structure.
            # A simple way for field-specific error in model_validator:
            raise ValueError("If downtime_enabled is true, downtime_days cannot be empty.")
            # Or for more complex Pydantic error reporting:
            # from pydantic import PydanticCustomError
            # raise PydanticCustomError("value_error", "downtime_days must be provided if downtime is enabled")
        
        # Call the parent's model validator if needed, or re-implement shared logic.
        # Since ParentalSettingsFields already has a time check, ensure it's compatible or called.
        # For simplicity, the check in ParentalSettingsFields will cover times if both are present.
        return self

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True, # Useful if DB uses _id and Pydantic uses id with alias
        validate_assignment=True,
        extra='ignore',
        use_enum_values=True, # When creating from dict, ensures string enums are handled
        json_schema_extra={
            "examples": [
                {
                    "block_violence": False, "block_inappropriate": True, "daily_limit_hours": "3",
                    "asd_level": "low", "downtime_enabled": True, "downtime_days": ["Fri", "Sat", "Sun"],
                    "downtime_start": "21:00", "downtime_end": "07:00", "require_passcode": True,
                    "notify_emails": ["guardian@example.com"], "data_sharing_preference": True,
                }
            ]
        }
    )


class ParentalSettingsRead(ParentalSettingsBase):
    """Schema for reading parental settings, includes the document ID."""
    id: str = Field(description="Unique identifier for the parental settings document.")
    # If your Beanie model uses `_id` and you want `id` in Pydantic with auto-conversion:
    # id: str = Field(alias='_id', description="Unique identifier...")

    model_config = ConfigDict(
        from_attributes=True, # Essential for reading from ORM/ODM models
        populate_by_name=True, # If using alias like '_id' for 'id'
        json_schema_extra={
            "example": {
                "id": "65f1b4a1d3e7b3d1e4a3c2d1", "block_violence": False, "block_inappropriate": True,
                "daily_limit_hours": "2", "asd_level": "medium", "downtime_enabled": True,
                "downtime_days": ["Fri", "Sat", "Sun"], "downtime_start": "21:00", "downtime_end": "07:00",
                "require_passcode": True, "notify_emails": ["parent@example.com"], "data_sharing_preference": False,
            }
        }
    )


class ParentalSettingsUpdateRequest(BaseModel):
    """
    Schema for the entire request body of a PATCH /parental endpoint.
    Contains optional metadata and a 'value' object with the actual settings to update.
    """
    description: Optional[str] = Field(None, description="Optional description for the update operation.", examples=["User onboarding preferences."])
    summary: Optional[str] = Field(None, description="Optional summary for the update operation.", examples=["Onboarding Settings"])
    value: ParentalSettingsFields # The actual settings fields to be updated, all optional within ParentalSettingsFields

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                   "summary": "Disable Downtime",
                   "description": "Example PATCH request to disable the downtime feature.",
                   "value": { "downtime_enabled": False }
                },
                {
                    "summary": "Change Daily Limit and Email",
                    "description": "Example PATCH updating the hour limit and notification list.",
                    "value": {
                        "daily_limit_hours": "5",
                        "notify_emails": ["parent1@example.com", "guardian@example.com"]
                    }
                },
                {
                    "summary": "Set ASD Level",
                    "description": "Example PATCH to set a specific ASD level.",
                    "value": { "asd_level": "medium" }
                },
            ]
        }
    )