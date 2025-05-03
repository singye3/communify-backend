# app/schemas/settings.py
import logging
from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    field_validator,
    model_validator,
    ConfigDict # Use ConfigDict for Pydantic v2 style configuration
)
from typing import Optional, List, Annotated, Dict, Any

# Assuming enums are defined correctly elsewhere
from app.db.models.enums import AsdLevel, DayOfWeek

# --- Constants ---
DAY_ORDER: List[DayOfWeek] = [
    DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED,
    DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN
]
TIME_PATTERN = r"^[0-2][0-9]:[0-5][0-9]$"
HOURS_PATTERN = r"^(?:[0-9]|1[0-9]|2[0-4])?$"

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Base Schema ---
class ParentalSettingsBase(BaseModel):
    """
    Base schema for parental control settings.
    Contains common fields used for creation, reading, and updating.
    Includes validation logic applicable to all operations.
    """
    block_violence: bool = Field(
        default=False,
        description="Block content categorized as violent."
    )
    block_inappropriate: bool = Field(
        default=False,
        description="Block content categorized as inappropriate for children."
    )
    daily_limit_hours: Optional[Annotated[str, Field(
        pattern=HOURS_PATTERN,
        default=None,
        examples=["", "2", "10", "24", None]
    )]] = Field(
        default=None,
        description="Daily screen time usage limit in hours (0-24). "
                    "Null or potentially empty string means no limit.",
    )
    asd_level: Optional[AsdLevel] = Field(
        default=None,
        description="Selected Autism Spectrum Disorder support level for tailored aids."
    )
    downtime_enabled: bool = Field(
        default=False,
        description="Enable scheduled downtime periods."
    )
    downtime_days: List[DayOfWeek] = Field(
        default_factory=list,
        description="List of days (e.g., ['Mon', 'Wed']) when downtime is active. "
                    "Will be automatically sorted.",
        examples=[[], ["Mon", "Fri"], ["Sat", "Sun", "Wed"]]
    )
    downtime_start: Annotated[str, Field(pattern=TIME_PATTERN)] = Field(
        default="21:00",
        description="Downtime start time in HH:MM (24-hour) format.",
        examples=["09:00", "22:30"]
    )
    downtime_end: Annotated[str, Field(pattern=TIME_PATTERN)] = Field(
        default="07:00",
        description="Downtime end time in HH:MM (24-hour) format.",
        examples=["17:00", "06:00"]
    )
    require_passcode: bool = Field(
        default=False,
        description="Require parental passcode for changing settings or exiting restricted modes."
    )
    notify_emails: List[EmailStr] = Field(
        default_factory=list,
        description="List of email addresses to receive usage reports or notifications.",
        examples=[[], ["parent@example.com"]]
    )
    data_sharing_preference: bool = Field(
        default=False,
        description="User preference regarding anonymous data sharing for improvement."
    )

    # --- Field Validators ---
    @field_validator('downtime_days', mode='before')
    @classmethod
    def validate_and_sort_downtime_days(cls, v: Any) -> List[DayOfWeek]:
        if not isinstance(v, list):
            raise ValueError("downtime_days must be provided as a list (e.g., ['Mon', 'Fri']).")
        valid_days_enum: set[DayOfWeek] = set()
        invalid_days: list[str] = []
        for item in v:
            try:
                day_enum = DayOfWeek(item)
                valid_days_enum.add(day_enum)
            except ValueError:
                invalid_days.append(str(item))
        if invalid_days:
            valid_options = ", ".join(d.value for d in DayOfWeek)
            raise ValueError(
                f"Invalid day(s) found in downtime_days: {', '.join(invalid_days)}. "
                f"Allowed values are: {valid_options}."
            )
        return sorted(list(valid_days_enum), key=lambda day: DAY_ORDER.index(day))

    # --- Model Validators ---
    @model_validator(mode='after')
    def check_downtime_config(self) -> 'ParentalSettingsBase':
        if self.downtime_enabled and not self.downtime_days:
            raise ValueError(
                {'downtime_days': 'At least one active day must be selected if downtime is enabled.'}
            )
        if self.downtime_start and self.downtime_end:
            try:
                start_h, start_m = map(int, self.downtime_start.split(':'))
                end_h, end_m = map(int, self.downtime_end.split(':'))
                start_total_minutes = start_h * 60 + start_m
                end_total_minutes = end_h * 60 + end_m
                if start_total_minutes == end_total_minutes:
                    error_detail = (
                        f"Downtime start time ({self.downtime_start}) cannot be "
                        f"the same as the end time ({self.downtime_end})."
                    )
                    raise ValueError({
                        'downtime_start': error_detail,
                        'downtime_end': error_detail
                    })
            except ValueError as e:
                if isinstance(getattr(e, 'errors', lambda: None)(), list): raise e # Check if structured
                if "cannot be the same" in str(e): raise e
                else:
                    logger.warning(f"Unexpected ValueError during downtime time parsing: Start='{self.downtime_start}', End='{self.downtime_end}'. Error: {e}")
                    raise ValueError({
                        'downtime_start': 'Invalid time format encountered.',
                        'downtime_end': 'Invalid time format encountered.'
                    }) from e
            except Exception as e:
                logger.exception("Unexpected error during downtime time validation logic:")
                raise ValueError("An internal error occurred during downtime time validation.")
        return self

    # --- Pydantic Configuration ---
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
        extra='ignore',
        json_schema_extra={ # Examples relevant to Base, Read, and potentially Create
            "examples": [
                { # Example 1: Basic, using defaults + overnight downtime
                    "block_violence": False, "block_inappropriate": True, "daily_limit_hours": "3",
                    "asd_level": "low", "downtime_enabled": True, "downtime_days": ["Fri", "Sat", "Sun"],
                    "downtime_start": "21:00", "downtime_end": "07:00", "require_passcode": True,
                    "notify_emails": ["guardian@example.com"], "data_sharing_preference": True,
                },
                { # Example 2: No downtime, no limit
                    "block_violence": False, "block_inappropriate": False, "daily_limit_hours": None,
                    "asd_level": None, "downtime_enabled": False, "downtime_days": [],
                    "downtime_start": "10:00", "downtime_end": "11:00", "require_passcode": False,
                    "notify_emails": [], "data_sharing_preference": False,
                },
                 { # Example 3: Same-day downtime
                    "block_violence": False, "block_inappropriate": True, "daily_limit_hours": "2",
                    "asd_level": "medium", "downtime_enabled": True, "downtime_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                    "downtime_start": "09:00", "downtime_end": "17:00", "require_passcode": True,
                    "notify_emails": ["parent1@example.com", "parent2@example.com"], "data_sharing_preference": True,
                },
            ]
        }
    )


# --- Schema for Reading Data ---
class ParentalSettingsRead(ParentalSettingsBase):
    """
    Schema for representing parental settings data read from the database.
    Includes the unique document identifier ('id').
    """
    id: str = Field(..., alias='_id', description="Unique identifier for the parental settings document.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "65f1b4a1d3e7b3d1e4a3c2d1", "block_violence": False, "block_inappropriate": True,
                "daily_limit_hours": "2", "asd_level": "medium", "downtime_enabled": True,
                "downtime_days": ["Fri", "Sat", "Sun"], "downtime_start": "21:00", "downtime_end": "07:00",
                "require_passcode": True, "notify_emails": ["parent@example.com"], "data_sharing_preference": False,
            }
        }
    )

# --- Schema for Updating Data ---
class ParentalSettingsUpdate(ParentalSettingsBase):
    """
    Schema specifically for **PATCH updates** to parental settings.

    Use this schema for request bodies in PATCH endpoints. Any field defined in
    `ParentalSettingsBase` can be included in the request payload.

    - **Partial Updates:** Only fields explicitly provided in the request body will be
      processed and validated. Fields omitted in the request remain unchanged in the database.
    - **Optionality:** All fields are implicitly optional for input.
    - **Validation:** Inherits ALL validation logic (field and model validators) from
      `ParentalSettingsBase`, ensuring data consistency for the fields being updated.
    - **Setting Null:** To clear an optional field (like `daily_limit_hours` or `asd_level`),
      explicitly include it in the payload with a `null` value (e.g., `"daily_limit_hours": null`).
    - **Usage:** In the endpoint logic, use `input_data.model_dump(exclude_unset=True)` to get a
      dictionary containing only the fields that were present in the request, ready for use
      with MongoDB's `$set` operator.
    """
    # No need to redefine fields. Simple inheritance makes all base fields
    # available and optional for input validation in Pydantic v2.
    pass

    # Configuration specific to the update schema
    model_config = ConfigDict(
        # Inherit common config like from_attributes, populate_by_name etc. from Base
        # Provide examples illustrating partial updates
        json_schema_extra={
            "examples": [ # Use a list for multiple, distinct PATCH examples
                {
                   "summary": "Disable Downtime", # Add summary for OpenAPI
                   "description": "Example PATCH request to disable the downtime feature.",
                   "value": {
                        "downtime_enabled": False
                        # Note: downtime_days, start/end times are not sent and remain unchanged.
                   }
                },
                {
                    "summary": "Change Daily Limit and Email",
                    "description": "Example PATCH updating the hour limit and notification list.",
                    "value": {
                        "daily_limit_hours": "5",
                        "notify_emails": ["parent1@example.com", "guardian@example.com"] # Replaces the entire list
                    }
                },
                {
                    "summary": "Clear ASD Level",
                    "description": "Example PATCH setting the ASD level back to null (not specified).",
                    "value": {
                        "asd_level": None # Explicitly setting to null
                    }
                },
                 {
                    "summary": "Update only Downtime Times",
                    "description": "Example PATCH changing only the start and end times for downtime.",
                    "value": {
                        "downtime_start": "08:30",
                        "downtime_end": "19:00" # Updates to a same-day period
                    }
                }
            ]
        }
    )