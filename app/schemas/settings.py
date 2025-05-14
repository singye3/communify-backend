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
from typing import Optional, List, Annotated, Any, Dict # Added Dict for validator

# Assuming enums are defined correctly in app.db.models.enums
from app.db.models.enums import AsdLevel, DayOfWeek

# --- Constants ---
DAY_ORDER_MAP: Dict[DayOfWeek, int] = { # Changed to map for easier lookup
    DayOfWeek.MON: 0, DayOfWeek.TUE: 1, DayOfWeek.WED: 2,
    DayOfWeek.THU: 3, DayOfWeek.FRI: 4, DayOfWeek.SAT: 5, DayOfWeek.SUN: 6
}
TIME_PATTERN = r"^(?:[01]\d|2[0-3]):(?:[0-5]\d)$" # HH:MM format (00:00 - 23:59)
# Allows empty string (for no limit), or 0-24. Validator will handle conversion/validation.
HOURS_PATTERN = r"^(?:[0-9]|1[0-9]|2[0-4])?$"


# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Schema for fields within the 'value' object of a PATCH request ---
# All fields are optional, as any subset can be updated.
class ParentalSettingsFieldsForUpdate(BaseModel):
    block_violence: Optional[bool] = Field(None, description="Block content categorized as violent.")
    block_inappropriate: Optional[bool] = Field(None, description="Block content categorized as inappropriate for children.")
    daily_limit_hours: Optional[Annotated[str, Field(pattern=HOURS_PATTERN)]] = Field(
        None,
        description="Daily screen time usage limit in hours (0-24). Null or empty string means no limit.",
        examples=["", "2", "10", "24", None] # Added "24"
    )
    # For asd_level, API expects "low", "medium", "high", or "noAsd" (string) for null.
    # Pydantic will validate incoming strings against AsdLevel enum.
    asd_level: Optional[AsdLevel] = Field(None, description="Selected Autism Spectrum Disorder support level. Use 'noAsd' for null/none.")
    downtime_enabled: Optional[bool] = Field(None, description="Enable scheduled downtime periods.")
    downtime_days: Optional[List[DayOfWeek]] = Field(None, description="Days when downtime is active. Expected as list of strings e.g. ['Mon', 'Tue']. Sorted automatically.")
    downtime_start: Optional[Annotated[str, Field(pattern=TIME_PATTERN)]] = Field(
        None, description="Downtime start time in HH:MM (24-hour).", examples=["09:00", "22:30"]
    )
    downtime_end: Optional[Annotated[str, Field(pattern=TIME_PATTERN)]] = Field(
        None, description="Downtime end time in HH:MM (24-hour).", examples=["17:00", "06:00"]
    )
    require_passcode: Optional[bool] = Field(None, description="Require passcode for changing settings.")
    notify_emails: Optional[List[EmailStr]] = Field(None, description="Emails for usage reports/notifications.")
    data_sharing_preference: Optional[bool] = Field(None, description="Preference for anonymous data sharing.")

    @field_validator('downtime_days', mode='before')
    @classmethod
    def validate_and_sort_downtime_days(cls, v: Optional[List[Any]]) -> Optional[List[DayOfWeek]]:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("downtime_days must be a list (e.g., ['Mon', 'Fri']) or null.")

        valid_days_enum_set: set[DayOfWeek] = set()
        invalid_items: list[str] = []
        for item in v:
            try:
                # Pydantic v2 with use_enum_values=True in config will handle string to enum.
                # Or, ensure DayOfWeek(str(item)) works if input might not be string.
                day_enum = DayOfWeek(str(item))
                valid_days_enum_set.add(day_enum)
            except ValueError: # Catches if str(item) is not a valid DayOfWeek value
                invalid_items.append(str(item))

        if invalid_items:
            valid_options = ", ".join(d.value for d in DayOfWeek) # Use .value for string representation
            raise ValueError(
                f"Invalid day(s) in downtime_days: {', '.join(invalid_items)}. Allowed: {valid_options}."
            )
        # Sort using the predefined order
        return sorted(list(valid_days_enum_set), key=lambda day_enum: DAY_ORDER_MAP[day_enum]) if valid_days_enum_set else []

    @field_validator('daily_limit_hours', mode='before')
    @classmethod
    def normalize_daily_limit_hours(cls, v: Any) -> Optional[str]:
        """Allows None, empty string (becomes None), or validates numeric string range 0-24."""
        if v is None or v == "":
            return None # Normalize empty string to None for consistency
        
        if not isinstance(v, str):
            if isinstance(v, (int, float)): # Allow numbers to be passed and convert
                if not (0 <= v <= 24):
                    raise ValueError("Daily limit hours must be between 0 and 24.")
                return str(int(v))
            raise ValueError("Daily limit hours must be a string or a number.")

        # If it's a string, it should match the pattern (which includes digits and emptiness)
        # The pattern on the field will do basic format check. Here we check numeric range.
        try:
            if v: # If not empty string (already handled)
                hour = int(v)
                if not (0 <= hour <= 24):
                    raise ValueError("Daily limit hours must be between 0 and 24.")
                return str(hour) # Return original valid string
            return None # Should have been caught by v == ""
        except ValueError as e: # Catches int conversion error or range error
             raise ValueError(f"Invalid daily limit hours value '{v}': {e}")


    @model_validator(mode='after')
    def check_downtime_logic(self) -> 'ParentalSettingsFieldsForUpdate':
        # This validator applies to the fields provided in a PATCH 'value' object.
        # 1. If downtime is enabled, days must be provided (unless days are also being patched to empty, which is complex to infer intent for)
        # 2. If start and end times are present, they should not be identical.

        # Check enabled and days consistency if downtime_enabled is explicitly part of the PATCH
        if self.downtime_enabled is True and self.downtime_days is not None and not self.downtime_days:
            # This situation means client is setting enabled=True but providing empty days list.
            raise ValueError("If enabling downtime, downtime_days cannot be empty in the same update.")
        
        # Check start/end time consistency if both are provided in the PATCH
        if self.downtime_start is not None and self.downtime_end is not None:
            try:
                start_h, start_m = map(int, self.downtime_start.split(':'))
                end_h, end_m = map(int, self.downtime_end.split(':'))
                if (start_h * 60 + start_m) == (end_h * 60 + end_m):
                    # To provide field-specific errors from model_validator, you'd typically collect
                    # errors and raise a single ValidationError, or use more advanced Pydantic features.
                    # For simplicity, FastAPI will wrap this ValueError.
                    raise ValueError("Downtime start and end times cannot be the same.")
            except ValueError as e: # Catch error from map/int or our custom ValueError
                if "cannot be the same" not in str(e): # Avoid re-wrapping our specific error
                    logger.warning(f"Invalid time format in PATCH: start='{self.downtime_start}', end='{self.downtime_end}'. Error: {e}")
                    raise ValueError("Invalid time format for downtime_start or downtime_end.")
                raise # Re-raise our "cannot be the same" error
            except Exception as e:
                logger.exception(f"Unexpected error validating downtime times in PATCH: {e}")
                raise ValueError("Internal error during downtime time validation.")
        return self

    model_config = ConfigDict(
        from_attributes=True,       # Allows Pydantic to read data from ORM model attributes
        validate_assignment=True,   # Validate fields on assignment after model creation
        extra='ignore',             # Ignore extra fields not defined in this schema during parsing
        use_enum_values=True,       # Expects string values for enums from client, validates against enum
    )


class ParentalSettingsBase(ParentalSettingsFieldsForUpdate): # Inherit structure and field validators
    """
    Base schema for parental settings, establishing non-Optional fields and
    default values for document CREATION.
    """
    # Override fields from ParentalSettingsFieldsForUpdate to make them non-optional
    # and provide creation-time defaults.
    block_violence: bool = False
    block_inappropriate: bool = False
    daily_limit_hours: Optional[Annotated[str, Field(pattern=HOURS_PATTERN)]] = None # Default is no limit
    asd_level: Optional[AsdLevel] = None # Default is no specific level, API/DB might use "noAsd" string or null
    downtime_enabled: bool = False
    downtime_days: List[DayOfWeek] = Field(default_factory=list) # Default is empty list
    downtime_start: Annotated[str, Field(pattern=TIME_PATTERN)] = "21:00"
    downtime_end: Annotated[str, Field(pattern=TIME_PATTERN)] = "07:00"
    require_passcode: bool = False
    notify_emails: List[EmailStr] = Field(default_factory=list)
    data_sharing_preference: bool = False

    # Model validator specific to creation/full update context
    @model_validator(mode='after')
    def check_downtime_config_on_full_update(self) -> 'ParentalSettingsBase':
        # This runs after individual field validations.
        # It applies when a full ParentalSettingsBase object is validated (e.g., on creation).
        if self.downtime_enabled and not self.downtime_days:
            raise ValueError("If downtime_enabled is true, downtime_days cannot be empty.")
        
        # The time consistency check from ParentalSettingsFieldsForUpdate will also apply here
        # because this model validator runs after the parent's.
        return self

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
        extra='ignore', # Important for creation from potentially wider dicts
        use_enum_values=True, # Ensures string enums from input are handled correctly
        json_schema_extra={
            "examples": [{
                "block_violence": False, "block_inappropriate": True, "daily_limit_hours": "3",
                "asd_level": "low", "downtime_enabled": True, "downtime_days": ["Fri", "Sat", "Sun"],
                "downtime_start": "21:00", "downtime_end": "07:00", "require_passcode": True,
                "notify_emails": ["guardian@example.com"], "data_sharing_preference": True,
            }]
        }
    )


class ParentalSettingsRead(ParentalSettingsBase): # Inherits defaults and structure
    """Schema for reading parental settings, includes the document ID."""
    id: str = Field(description="Unique identifier for the parental settings document.")
    # If your Beanie model uses `_id` and you want `id` in Pydantic with auto-conversion:
    # id: str = Field(alias='_id', description="Unique identifier...")
    # Ensure created_at and updated_at are present if needed in response
    # created_at: datetime 
    # updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True, # Essential for creating from ORM/ODM model instances
        populate_by_name=True, # If using alias for 'id'
        json_schema_extra={ "example": { # Update example to match fields
                "id": "65f1b4a1d3e7b3d1e4a3c2d1", "block_violence": False, "block_inappropriate": True,
                "daily_limit_hours": "2", "asd_level": "medium", "downtime_enabled": True,
                "downtime_days": ["Fri", "Sat", "Sun"], "downtime_start": "21:00", "downtime_end": "07:00",
                "require_passcode": True, "notify_emails": ["parent@example.com"], "data_sharing_preference": False,
        }}
    )


class ParentalSettingsUpdateRequest(BaseModel):
    """
    Schema for the entire request body of a PATCH /parental endpoint.
    """
    description: Optional[str] = Field(None, description="Optional description for the update.", examples=["User onboarding preferences."])
    summary: Optional[str] = Field(None, description="Optional summary for the update.", examples=["Onboarding Settings"])
    value: ParentalSettingsFieldsForUpdate # The actual settings fields to be updated

    model_config = ConfigDict(
        json_schema_extra={ "examples": [{
                   "summary": "Disable Downtime",
                   "description": "Example PATCH to disable the downtime feature.",
                   "value": { "downtime_enabled": False }
                },{
                    "summary": "Update Limit & Email",
                    "value": { "daily_limit_hours": "5", "notify_emails": ["parent1@example.com"] }
                },{
                    "summary": "Set ASD Level", "value": { "asd_level": "medium" }
                },
        ]}
    )