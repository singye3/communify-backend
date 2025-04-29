# app/schemas/settings.py
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator # Added model_validator
from typing import Optional, List, Annotated # Added Annotated
from app.db.models.enums import AsdLevel, DayOfWeek
from datetime import time 

# --- Base Schema ---
class ParentalSettingsBase(BaseModel):
    block_violence: bool = Field(
        default=False,
        description="Block content categorized as violent."
    )
    block_inappropriate: bool = Field(
        default=False,
        description="Block content categorized as inappropriate for children."
    )
    # Using Optional[str] with pattern allows null/empty string/valid hours. Ensure backend logic handles these cases.
    # Alternatively, use Optional[Annotated[int, Field(ge=0, le=24)]] if only null means "no limit".
    daily_limit_hours: Optional[Annotated[str, Field(pattern=r"^(?:[0-9]|1[0-9]|2[0-4])?$", default=None)]] = Field(
        default=None, # Explicit default None
        description="Daily screen time usage limit in hours (0-24, empty/null means no limit)."
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
        description="List of days when downtime is active (e.g., ['Mon', 'Wed', 'Fri'])."
    )
    downtime_start: Annotated[str, Field(pattern=r"^[0-2][0-9]:[0-5][0-9]$")] = Field(
        default="21:00",
        description="Downtime start time in HH:MM (24-hour) format."
    )
    downtime_end: Annotated[str, Field(pattern=r"^[0-2][0-9]:[0-5][0-9]$")] = Field(
        default="07:00",
        description="Downtime end time in HH:MM (24-hour) format."
    )
    require_passcode: bool = Field(
        default=False,
        description="Require parental passcode for changing settings or exiting restricted modes."
    )
    notify_emails: List[EmailStr] = Field(
        default_factory=list,
        description="List of email addresses to receive usage reports or notifications."
    )
    data_sharing_preference: bool = Field(
        default=False,
        description="User preference regarding anonymous data sharing for improvement."
    )


    # --- Field Validators ---
    @field_validator('downtime_days', mode='before')
    @classmethod
    def sort_and_validate_days(cls, v):
        if not isinstance(v, list):
            # Allow Pydantic to handle non-list types later if needed, or raise error here
             return v # Or raise TypeError('downtime_days must be a list')
        try:
            # Define the canonical order
            day_order: List[DayOfWeek] = [DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN]
            # Validate and convert to Enum members, remove duplicates
            valid_days_enum = {DayOfWeek(item) for item in v if item in DayOfWeek.__members__.values()}
            # Sort the valid Enum members based on the canonical order
            return sorted(list(valid_days_enum), key=lambda day: day_order.index(day))
        except ValueError as e:
            # Catch specific error if an invalid day string is provided
            raise ValueError(f"Invalid day found in downtime_days: {v}. Must be one of {', '.join(d.value for d in DayOfWeek)}") from e

    # --- Model Validators ---
    @model_validator(mode='after') # Use 'after' to access validated fields
    def check_downtime_days_if_enabled(self):
        # Access fields via self after initial validation
        if self.downtime_enabled and not self.downtime_days:
            raise ValueError('If downtime is enabled, at least one active day must be selected.')
        return self

    @model_validator(mode='after')
    def check_downtime_hours_order(self):
        # Check if both times are provided (already validated for format by Field)
        if self.downtime_start and self.downtime_end:
            try:
                start_h, start_m = map(int, self.downtime_start.split(':'))
                end_h, end_m = map(int, self.downtime_end.split(':'))
                start_total_minutes = start_h * 60 + start_m
                end_total_minutes = end_h * 60 + end_m

                # **REFINED LOGIC**: Example: Ensure start time is strictly before end time.
                # Assumes downtime does NOT span across midnight (e.g., 22:00 to 06:00 is invalid here).
                # Adjust this logic if overnight downtime IS allowed.
                if start_total_minutes >= end_total_minutes:
                    raise ValueError('Downtime start time must be strictly before the end time (HH:MM). Overnight periods spanning midnight require different handling.')

            except ValueError as e:
                # Re-raise specific validation error, avoid catching generic ValueErrors from elsewhere
                if 'time format' not in str(e) and 'must be strictly before' not in str(e):
                     # This should ideally not be reached if Field pattern works, but as a fallback:
                     raise ValueError(f'Invalid time format encountered: {e}')
                else:
                    raise e # Raise the specific format or comparison error
            except Exception as e: # Catch any unexpected errors during validation
                # Log this unexpected error
                print(f"Unexpected error during downtime validation: {e}")
                raise ValueError("An unexpected error occurred during downtime time validation.")
        return self


    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "block_violence": False,
                "block_inappropriate": True,
                "daily_limit_hours": "2",
                "asd_level": "medium",
                "downtime_enabled": True,
                "downtime_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                "downtime_start": "20:30",
                "downtime_end": "22:00", # Changed example to be valid with new validator
                "require_passcode": True,
                "notify_emails": ["parent1@example.com", "guardian@example.com"],
                "data_sharing_preference": False,
            }
        }


# --- Schema for Reading Data ---
class ParentalSettingsRead(ParentalSettingsBase):
    id: str = Field(..., alias='_id', description="Unique identifier for the parental settings document.")

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = { # Example specific to Read
            "example": {
                "id": "6811a5b...",
                "block_violence": False,
                "block_inappropriate": True,
                "daily_limit_hours": "2",
                "asd_level": "medium",
                "downtime_enabled": True,
                "downtime_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                "downtime_start": "20:30",
                "downtime_end": "22:00", # Changed example
                "require_passcode": True,
                "notify_emails": ["parent1@example.com", "guardian@example.com"],
                "data_sharing_preference": False,
            }
        }


# --- Schema for Updating Data ---
# **REFINED**: No need to redeclare fields as Optional = None here.
# Pydantic handles making inherited fields optional for input automatically.
class ParentalSettingsUpdate(ParentalSettingsBase):
    pass # Inherits all fields from Base as optional for input

    class Config:
        # Keep configuration like examples if needed
        from_attributes = True # Ensure config is inherited or re-declared if needed
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "downtime_enabled": False, # Example: disabling downtime
                "daily_limit_hours": "3",   # Example: updating limit
                "notify_emails": ["parent1@example.com"], # Example: replacing list
                "downtime_days": ["Sat", "Sun"] # Example: changing days
            }
        }