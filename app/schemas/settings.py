# app/schemas/settings.py
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from enum import Enum

# Re-define enums used in frontend/models for API validation
class AsdLevel(str, Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    NO_ASD = 'noAsd' # Match frontend value

class DayOfWeek(str, Enum):
    MON = 'Mon'
    TUE = 'Tue'
    WED = 'Wed'
    THU = 'Thu'
    FRI = 'Fri'
    SAT = 'Sat'
    SUN = 'Sun'

# Base schema for parental settings data
class ParentalSettingsBase(BaseModel):
    block_violence: Optional[bool] = Field(default=False)
    block_inappropriate: Optional[bool] = Field(default=False)
    daily_limit_hours: Optional[str] = Field(default=None, pattern=r"^(?:[0-9]|1[0-9]|2[0-4])?$") # Allow empty or 0-24
    asd_level: Optional[AsdLevel] = Field(default=None)
    downtime_enabled: Optional[bool] = Field(default=False)
    downtime_days: Optional[List[DayOfWeek]] = Field(default_factory=list)
    downtime_start: Optional[str] = Field(default="21:00", pattern=r"^[0-2][0-9]:[0-5][0-9]$") # Basic time format HH:MM
    downtime_end: Optional[str] = Field(default="07:00", pattern=r"^[0-2][0-9]:[0-5][0-9]$")
    require_passcode: Optional[bool] = Field(default=False)
    notify_emails: Optional[List[EmailStr]] = Field(default_factory=list)

    # Optional validator
    @field_validator('downtime_days', mode='before')
    @classmethod
    def sort_days(cls, v):
        if isinstance(v, list):
            day_order: List[DayOfWeek] = [DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN]
            # Use a set for efficient checking and filter valid days
            valid_days = set(item for item in v if item in day_order)
            # Sort based on predefined order
            return sorted(list(valid_days), key=lambda day: day_order.index(day))
        return v

# Schema for updating settings (all fields optional)
class ParentalSettingsUpdate(ParentalSettingsBase):
    pass

# Schema for reading settings (includes ID and potentially user ID)
class ParentalSettingsRead(ParentalSettingsBase):
    id: str = Field(..., alias='_id')
    # user_id: str # Or however you want to represent the user link

    class Config:
        from_attributes = True
        populate_by_name = True # Pydantic v2 for alias