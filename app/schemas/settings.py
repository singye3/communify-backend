# app/schemas/settings.py
import logging
from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    field_validator,
    model_validator,
    ConfigDict,
)
from typing import Optional, List, Annotated, Any, Dict
from app.db.models.enums import AsdLevel, DayOfWeek

# --- Constants ---
DAY_ORDER_MAP: Dict[DayOfWeek, int] = {
    DayOfWeek.MON: 0,
    DayOfWeek.TUE: 1,
    DayOfWeek.WED: 2,
    DayOfWeek.THU: 3,
    DayOfWeek.FRI: 4,
    DayOfWeek.SAT: 5,
    DayOfWeek.SUN: 6,
}
TIME_PATTERN = r"^(?:[01]\d|2[0-3]):(?:[0-5]\d)$"  # HH:MM format (00:00 - 23:59)
HOURS_PATTERN = r"^(?:[0-9]|1[0-9]|2[0-4])?$"


# --- Module Logger ---
logger = logging.getLogger(__name__)


# --- Schema for fields within the 'value' object of a PATCH request ---
class ParentalSettingsFieldsForUpdate(BaseModel):
    block_violence: Optional[bool] = Field(
        None, description="Block content categorized as violent."
    )
    block_inappropriate: Optional[bool] = Field(
        None, description="Block content categorized as inappropriate for children."
    )
    daily_limit_hours: Optional[Annotated[str, Field(pattern=HOURS_PATTERN)]] = Field(
        None,
        description="Daily screen time usage limit in hours (0-24). Null or empty string means no limit.",
        examples=["", "2", "10", "24", None],  # Added "24"
    )
    asd_level: Optional[AsdLevel] = Field(
        None,
        description="Selected Autism Spectrum Disorder support level. Use 'noAsd' for null/none.",
    )
    downtime_enabled: Optional[bool] = Field(
        None, description="Enable scheduled downtime periods."
    )
    downtime_days: Optional[List[DayOfWeek]] = Field(
        None,
        description="Days when downtime is active. Expected as list of strings e.g. ['Mon', 'Tue']. Sorted automatically.",
    )
    downtime_start: Optional[Annotated[str, Field(pattern=TIME_PATTERN)]] = Field(
        None,
        description="Downtime start time in HH:MM (24-hour).",
        examples=["09:00", "22:30"],
    )
    downtime_end: Optional[Annotated[str, Field(pattern=TIME_PATTERN)]] = Field(
        None,
        description="Downtime end time in HH:MM (24-hour).",
        examples=["17:00", "06:00"],
    )
    require_passcode: Optional[bool] = Field(
        None, description="Require passcode for changing settings."
    )
    notify_emails: Optional[List[EmailStr]] = Field(
        None, description="Emails for usage reports/notifications."
    )
    data_sharing_preference: Optional[bool] = Field(
        None, description="Preference for anonymous data sharing."
    )

    @field_validator("downtime_days", mode="before")
    @classmethod
    def validate_and_sort_downtime_days(
        cls, v: Optional[List[Any]]
    ) -> Optional[List[DayOfWeek]]:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError(
                "downtime_days must be a list (e.g., ['Mon', 'Fri']) or null."
            )

        valid_days_enum_set: set[DayOfWeek] = set()
        invalid_items: list[str] = []
        for item in v:
            try:
                day_enum = DayOfWeek(str(item))
                valid_days_enum_set.add(day_enum)
            except ValueError:
                invalid_items.append(str(item))

        if invalid_items:
            valid_options = ", ".join(d.value for d in DayOfWeek)
            raise ValueError(
                f"Invalid day(s) in downtime_days: {', '.join(invalid_items)}. Allowed: {valid_options}."
            )
        return (
            sorted(
                list(valid_days_enum_set), key=lambda day_enum: DAY_ORDER_MAP[day_enum]
            )
            if valid_days_enum_set
            else []
        )

    @field_validator("daily_limit_hours", mode="before")
    @classmethod
    def normalize_daily_limit_hours(cls, v: Any) -> Optional[str]:
        """Allows None, empty string (becomes None), or validates numeric string range 0-24."""
        if v is None or v == "":
            return None
        if not isinstance(v, str):
            if isinstance(v, (int, float)):
                if not (0 <= v <= 24):
                    raise ValueError("Daily limit hours must be between 0 and 24.")
                return str(int(v))
            raise ValueError("Daily limit hours must be a string or a number.")
        try:
            if v:
                hour = int(v)
                if not (0 <= hour <= 24):
                    raise ValueError("Daily limit hours must be between 0 and 24.")
                return str(hour)
            return None
        except ValueError as e:
            raise ValueError(f"Invalid daily limit hours value '{v}': {e}")

    @model_validator(mode="after")
    def check_downtime_logic(self) -> "ParentalSettingsFieldsForUpdate":
        if (
            self.downtime_enabled is True
            and self.downtime_days is not None
            and not self.downtime_days
        ):
            raise ValueError(
                "If enabling downtime, downtime_days cannot be empty in the same update."
            )
        if self.downtime_start is not None and self.downtime_end is not None:
            try:
                start_h, start_m = map(int, self.downtime_start.split(":"))
                end_h, end_m = map(int, self.downtime_end.split(":"))
                if (start_h * 60 + start_m) == (end_h * 60 + end_m):
                    raise ValueError("Downtime start and end times cannot be the same.")
            except ValueError as e:
                if "cannot be the same" not in str(e):
                    logger.warning(
                        f"Invalid time format in PATCH: start='{self.downtime_start}', end='{self.downtime_end}'. Error: {e}"
                    )
                    raise ValueError(
                        "Invalid time format for downtime_start or downtime_end."
                    )
                raise
            except Exception as e:
                logger.exception(
                    f"Unexpected error validating downtime times in PATCH: {e}"
                )
                raise ValueError("Internal error during downtime time validation.")
        return self

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        extra="ignore",
        use_enum_values=True,
    )


class ParentalSettingsBase(ParentalSettingsFieldsForUpdate):
    """
    Base schema for parental settings, establishing non-Optional fields and
    default values for document CREATION.
    """

    block_violence: bool = False
    block_inappropriate: bool = False
    daily_limit_hours: Optional[Annotated[str, Field(pattern=HOURS_PATTERN)]] = None
    asd_level: Optional[AsdLevel] = None
    downtime_enabled: bool = False
    downtime_days: List[DayOfWeek] = Field(default_factory=list)
    downtime_start: Annotated[str, Field(pattern=TIME_PATTERN)] = "21:00"
    downtime_end: Annotated[str, Field(pattern=TIME_PATTERN)] = "07:00"
    require_passcode: bool = False
    notify_emails: List[EmailStr] = Field(default_factory=list)
    data_sharing_preference: bool = False

    # Model validator specific to creation/full update context
    @model_validator(mode="after")
    def check_downtime_config_on_full_update(self) -> "ParentalSettingsBase":
        if self.downtime_enabled and not self.downtime_days:
            raise ValueError(
                "If downtime_enabled is true, downtime_days cannot be empty."
            )
        return self

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
        extra="ignore",
        use_enum_values=True,
        json_schema_extra={
            "examples": [
                {
                    "block_violence": False,
                    "block_inappropriate": True,
                    "daily_limit_hours": "3",
                    "asd_level": "low",
                    "downtime_enabled": True,
                    "downtime_days": ["Fri", "Sat", "Sun"],
                    "downtime_start": "21:00",
                    "downtime_end": "07:00",
                    "require_passcode": True,
                    "notify_emails": ["guardian@example.com"],
                    "data_sharing_preference": True,
                }
            ]
        },
    )


class ParentalSettingsRead(ParentalSettingsBase):  # Inherits defaults and structure
    """Schema for reading parental settings, includes the document ID."""

    id: str = Field(description="Unique identifier for the parental settings document.")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "65f1b4a1d3e7b3d1e4a3c2d1",
                "block_violence": False,
                "block_inappropriate": True,
                "daily_limit_hours": "2",
                "asd_level": "medium",
                "downtime_enabled": True,
                "downtime_days": ["Fri", "Sat", "Sun"],
                "downtime_start": "21:00",
                "downtime_end": "07:00",
                "require_passcode": True,
                "notify_emails": ["parent@example.com"],
                "data_sharing_preference": False,
            }
        },
    )


class ParentalSettingsUpdateRequest(BaseModel):
    """
    Schema for the entire request body of a PATCH /parental endpoint.
    """

    description: Optional[str] = Field(
        None,
        description="Optional description for the update.",
        examples=["User onboarding preferences."],
    )
    summary: Optional[str] = Field(
        None,
        description="Optional summary for the update.",
        examples=["Onboarding Settings"],
    )
    value: ParentalSettingsFieldsForUpdate

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Disable Downtime",
                    "description": "Example PATCH to disable the downtime feature.",
                    "value": {"downtime_enabled": False},
                },
                {
                    "summary": "Update Limit & Email",
                    "value": {
                        "daily_limit_hours": "5",
                        "notify_emails": ["parent1@example.com"],
                    },
                },
                {"summary": "Set ASD Level", "value": {"asd_level": "medium"}},
            ]
        }
    )
