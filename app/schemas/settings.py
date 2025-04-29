# app/schemas/settings.py
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator # Added model_validator
from typing import Optional, List, Annotated # Added Annotated
from enum import Enum
from datetime import time 

# --- Enums ---
class AsdLevel(str, Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    NO_ASD = 'noAsd'

class DayOfWeek(str, Enum):
    MON = 'Mon'
    TUE = 'Tue'
    WED = 'Wed'
    THU = 'Thu'
    FRI = 'Fri'
    SAT = 'Sat'
    SUN = 'Sun'

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
            return v
        try:
            day_order: List[DayOfWeek] = [DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN]
            valid_days = {DayOfWeek(item) for item in v if item in DayOfWeek.__members__.values()}
            return sorted(list(valid_days), key=lambda day: day_order.index(day))
        except ValueError:
            raise ValueError(f"Invalid day found in downtime_days: {v}. Must be one of {', '.join(d.value for d in DayOfWeek)}")

    # --- Model Validators ---
    @model_validator(mode='after') # Use 'after' to access validated fields
    def check_downtime_days_if_enabled(self):
        if self.downtime_enabled and not self.downtime_days:
            raise ValueError('If downtime is enabled, at least one active day must be selected.')
        return self

    @model_validator(mode='after')
    def check_downtime_hours_order(self):
        if self.downtime_start and self.downtime_end:
            try:
                start_h, start_m = map(int, self.downtime_start.split(':'))
                end_h, end_m = map(int, self.downtime_end.split(':'))
                start_total_minutes = start_h * 60 + start_m
                end_total_minutes = end_h * 60 + end_m

            except ValueError:
                raise ValueError('Invalid time format for downtime start or end.') # Should be caught by Field pattern
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
                "downtime_end": "06:30",
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
                "downtime_end": "06:30",
                "require_passcode": True,
                "notify_emails": ["parent1@example.com", "guardian@example.com"],
                "data_sharing_preference": False,
            }
        }


# --- Schema for Updating Data ---
class ParentalSettingsUpdate(ParentalSettingsBase):
    block_violence: Optional[bool] = None
    block_inappropriate: Optional[bool] = None
    daily_limit_hours: Optional[Annotated[str, Field(pattern=r"^(?:[0-9]|1[0-9]|2[0-4])?$")]] = None # Allow null/empty string to clear limit
    asd_level: Optional[AsdLevel] = None
    downtime_enabled: Optional[bool] = None
    downtime_days: Optional[List[DayOfWeek]] = None # Allow sending full list or null
    downtime_start: Optional[Annotated[str, Field(pattern=r"^[0-2][0-9]:[0-5][0-9]$")]] = None
    downtime_end: Optional[Annotated[str, Field(pattern=r"^[0-2][0-9]:[0-5][0-9]$")]] = None
    require_passcode: Optional[bool] = None
    notify_emails: Optional[List[EmailStr]] = None # Allow sending full list or null
    data_sharing_preference: Optional[bool] = None


    class Config:
        json_schema_extra = {
            "example": {
                "downtime_enabled": False,
                "daily_limit_hours": "3",
                "notify_emails": ["parent1@example.com"]
            }
        }