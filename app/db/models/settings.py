# app/db/models/settings.py

import logging
from typing import Optional, List, Annotated, Any
from datetime import datetime
from beanie import Document, Link, Indexed
from pydantic import Field, EmailStr, field_validator, model_validator
from .enums import AsdLevel, DayOfWeek

logger = logging.getLogger(__name__)

class ParentalSettings(Document):
    user: Annotated[Link["User"], Indexed(unique=True)]
    block_violence: bool = Field(
        default=False, description="Block content categorized as violent."
    )
    block_inappropriate: bool = Field(
        default=False,
        description="Block content categorized as inappropriate for children.",
    )
    daily_limit_hours: Optional[str] = Field(
        default=None,
        pattern=r"^(?:[0-9]|1[0-9]|2[0-4])?$",
        description="Daily screen time limit in hours (0-24). Null or empty means no limit.",
    )
    downtime_enabled: bool = Field(
        default=False, description="Enable scheduled downtime periods."
    )
    downtime_days: List[DayOfWeek] = Field(
        default_factory=list,
        description="List of days (Mon-Sun) when downtime is active.",
    )
    downtime_start: str = Field(
        default="21:00",
        pattern=r"^(?:[01]\d|2[0-3]):(?:[0-5]\d)$",
        description="Downtime start time in HH:MM (24-hour) format.",
    )
    downtime_end: str = Field(
        default="07:00",
        pattern=r"^(?:[01]\d|2[0-3]):(?:[0-5]\d)$",
        description="Downtime end time in HH:MM (24-hour) format.",
    )
    require_passcode: bool = Field(
        default=False,
        description="Require parental passcode for changing settings or exiting restricted modes.",
    )
    hashed_parental_passcode: Optional[str] = Field(
        None, description="Stores the hashed parental passcode."
    )
    notify_emails: List[EmailStr] = Field(
        default_factory=list,
        description="List of email addresses for notifications/reports.",
    )
    asd_level: Optional[AsdLevel] = Field(
        default=None,
        description="Selected Autism Spectrum Disorder support level.",
    )
    data_sharing_preference: bool = Field(
        default=False, description="User preference for anonymous data sharing."
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "parental_settings"

    async def before_save(self, *args: Any, **kwargs: Any) -> None:
        self.updated_at = datetime.utcnow()

    @field_validator("downtime_days", mode="before")
    @classmethod
    def sort_and_validate_downtime_days(cls, v: Any) -> List[DayOfWeek]:
        if not isinstance(v, list):
            raise ValueError("downtime_days must be a list.")
        day_order_map: Dict[DayOfWeek, int] = {
            DayOfWeek.MON: 0,
            DayOfWeek.TUE: 1,
            DayOfWeek.WED: 2,
            DayOfWeek.THU: 3,
            DayOfWeek.FRI: 4,
            DayOfWeek.SAT: 5,
            DayOfWeek.SUN: 6,
        }
        valid_days_enum_set = set()
        invalid_items = []
        for item in v:
            try:
                day_enum_member = DayOfWeek(item)
                valid_days_enum_set.add(day_enum_member)
            except ValueError:
                invalid_items.append(item)
        if invalid_items:
            allowed_values = ", ".join(d.value for d in DayOfWeek)
            raise ValueError(
                f"Invalid day(s) in downtime_days: {invalid_items}. Allowed: {allowed_values}."
            )
        return sorted(
            list(valid_days_enum_set), key=lambda day_enum: day_order_map[day_enum]
        )

    @field_validator("daily_limit_hours", mode="before")
    @classmethod
    def validate_optional_hour_string(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            if isinstance(v, (int, float)) and 0 <= v <= 24:
                return str(int(v))
            raise ValueError(
                "Daily limit hours must be a string representing a number."
            )
        if not v.isdigit():
            raise ValueError(
                "Limit must be a whole number string (e.g., '2', '10') if provided."
            )
        try:
            hour = int(v)
            if not (0 <= hour <= 24):
                raise ValueError(
                    "Daily limit hours must be between 0 and 24 inclusive."
                )
            return str(hour)
        except ValueError as e:
            raise ValueError(f"Invalid daily limit hours value '{v}': {e}")

    @model_validator(mode="after")
    def check_downtime_enabled_dependencies(self) -> "ParentalSettings":
        if self.downtime_enabled and not self.downtime_days:
            raise ValueError(
                "If downtime is enabled, at least one active day (downtime_days) must be selected."
            )
        return self

    @model_validator(mode="after")
    def check_passcode_requirement(self) -> "ParentalSettings":
        if self.require_passcode:
            logger.debug(
                "ParentalSettings model indicates require_passcode=True. External check for passcode existence is necessary."
            )
        return self

from .user import User
ParentalSettings.model_rebuild(force=True)