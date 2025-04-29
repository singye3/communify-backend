# app/db/models/settings.py
from typing import Optional, List, Annotated, Any
from datetime import datetime, time
from beanie import Document, Link, Indexed
from pydantic import Field, EmailStr, field_validator, model_validator, ValidationError
from .enums import AsdLevel, DayOfWeek



class ParentalSettings(Document):
    user: Annotated[Link["User"], Indexed(unique=True)] 
    block_violence: bool = Field(default=False)
    block_inappropriate: bool = Field(default=False)
    daily_limit_hours: Optional[str] = Field(default=None, pattern=r"^(?:[0-9]|1[0-9]|2[0-4])?$")
    asd_level: Optional[AsdLevel] = Field(default=None)
    downtime_enabled: bool = Field(default=False)
    downtime_days: List[DayOfWeek] = Field(default_factory=list)
    downtime_start: str = Field(default="21:00", pattern=r"^[0-2][0-9]:[0-5][0-9]$")
    downtime_end: str = Field(default="07:00", pattern=r"^[0-2][0-9]:[0-5][0-9]$")
    require_passcode: bool = Field(default=False)
    notify_emails: List[EmailStr] = Field(default_factory=list) 
    data_sharing_preference: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    class Settings:
        name = "parental_settings"
    async def before_save(self):
        """Automatically update 'updated_at' before saving."""
        self.updated_at = datetime.now()

    # --- Field Validators ---
    @field_validator('downtime_days', mode='before')
    @classmethod
    def sort_and_validate_downtime_days(cls, v: Any) -> List[DayOfWeek]:
        """Sorts and validates the list of downtime days upon setting/updating."""
        if not isinstance(v, list):
             raise ValueError('downtime_days must be a list')
        try:
            day_order: List[DayOfWeek] = [
                DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED,
                DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN
            ]
            valid_days = {DayOfWeek(item) for item in v if item in DayOfWeek.__members__.values()}
            return sorted(list(valid_days), key=lambda day: day_order.index(day))
        except ValueError as e:
            raise ValueError(f"Invalid day found in downtime_days. Must be one of {', '.join(d.value for d in DayOfWeek)}") from e

    @field_validator('daily_limit_hours', mode='before')
    @classmethod
    def validate_optional_hour_string(cls, v: Any) -> Optional[str]:
        """Allows None or empty string, otherwise validates numeric range 0-24."""
        if v is None or v == "":
            return None 
        try:
            if not isinstance(v, str) or not v.isdigit():
                 raise ValueError("Limit must be a whole number string if provided.")
            hour = int(v)
            if not (0 <= hour <= 24):
                raise ValueError("Daily limit hours must be between 0 and 24.")
            return str(hour) 
        except (ValueError, TypeError) as e:
             raise ValueError(f"Invalid daily limit '{v}': {e}") from e


    # --- Model Validators ---
    @model_validator(mode='after')
    def check_downtime_settings(self):
        """
        Ensures that if downtime is enabled:
        1. At least one day must be selected.
        2. Start and end times are valid HH:MM (pattern check handles format).
        """
        if self.downtime_enabled:
            if not self.downtime_days:
                raise ValueError('If downtime is enabled, at least one active day must be selected.')
            try:
                time.fromisoformat(self.downtime_start)
                time.fromisoformat(self.downtime_end)
            except ValueError:
                 raise ValueError('Invalid time format for downtime start or end. Use HH:MM.')

        return self

    @model_validator(mode='after')
    def check_passcode_requirement(self):
        """
        Placeholder: If require_passcode becomes true, potentially trigger
        a check elsewhere (e.g., in an endpoint) to ensure a passcode exists
        in the Keychain before allowing the save. This model can't directly
        check the Keychain.
        """
        if self.require_passcode:
            pass 
        return self


# Forward Reference Resolution
from .user import User
ParentalSettings.model_rebuild()