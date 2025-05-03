# app/schemas/settings.py
import logging # Import logging
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import Optional, List, Annotated
from app.db.models.enums import AsdLevel, DayOfWeek
# No need to import `time` from datetime if not used directly

# Get a logger instance for potential logging within validators
logger = logging.getLogger(__name__)

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
        default=None,
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
    # Default times now represent a valid overnight period with the updated validator
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
             return v # Allow Pydantic's deeper validation or raise TypeError here if strict list required
        try:
            day_order: List[DayOfWeek] = [DayOfWeek.MON, DayOfWeek.TUE, DayOfWeek.WED, DayOfWeek.THU, DayOfWeek.FRI, DayOfWeek.SAT, DayOfWeek.SUN]
            # Use values() for checking membership in Enum values directly
            valid_days_enum = {DayOfWeek(item) for item in v if isinstance(item, str) and item in DayOfWeek._value2member_map_}
            return sorted(list(valid_days_enum), key=lambda day: day_order.index(day))
        except ValueError as e:
            # Catch specific error if an invalid day string is provided
            raise ValueError(f"Invalid day found in downtime_days: {v}. Must be one of {', '.join(d.value for d in DayOfWeek)}") from e
        except Exception as e: # Catch unexpected errors during processing
            logger.error(f"Unexpected error sorting/validating downtime_days '{v}': {e}")
            raise ValueError(f"Failed to process downtime_days: {v}")


    # --- Model Validators ---
    @model_validator(mode='after')
    def check_downtime_days_if_enabled(self):
        if self.downtime_enabled and not self.downtime_days:
            # Raise error with field name for better frontend feedback
            raise ValueError({'downtime_days': 'If downtime is enabled, at least one active day must be selected.'})
        return self

    # --- REVISED MODEL VALIDATOR ---
    @model_validator(mode='after')
    def check_downtime_hours_order_and_allow_overnight(self):
        """
        Validates the downtime start and end times.
        Allows overnight periods (e.g., 21:00 to 07:00).
        Raises an error only if the start and end times are exactly the same.
        """
        # Only run validation if both times are present (format already checked by Field)
        if self.downtime_start and self.downtime_end:
            try:
                start_h, start_m = map(int, self.downtime_start.split(':'))
                end_h, end_m = map(int, self.downtime_end.split(':'))
                start_total_minutes = start_h * 60 + start_m
                end_total_minutes = end_h * 60 + end_m

                # Check for the only strictly invalid case: start time is identical to end time.
                # If start > end, we now interpret it as a valid overnight period.
                if start_total_minutes == end_total_minutes:
                    # Raise error indicating the specific problem and potentially targeting fields
                    error_detail = f"Downtime start time ({self.downtime_start}) cannot be the same as the end time ({self.downtime_end})."
                    # Pydantic v2 allows raising ValueError directly, or you can structure for FastAPI detail
                    raise ValueError(error_detail)
                    # Alternatively, for more structured FastAPI errors:
                    # raise ValueError({'downtime_start': error_detail, 'downtime_end': error_detail})


            except ValueError as e:
                # Re-raise our specific validation error directly
                if "cannot be the same as the end time" in str(e):
                     raise e
                # Otherwise, it might be an unexpected format error from map/int (though Field pattern should catch it)
                else:
                     logger.warning(f"Unexpected ValueError during downtime time parsing (Field pattern might have failed?): {self.downtime_start}, {self.downtime_end} -> {e}")
                     raise ValueError(f"Invalid time format encountered for start/end time: {e}") from e
            except Exception as e:
                # Catch any other unexpected errors during validation
                logger.exception("Unexpected error during downtime time validation:") # Use exception logger
                raise ValueError("An unexpected error occurred during downtime time validation.")
        return self # Always return self for model validators

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
                "downtime_start": "21:00", # Default overnight start
                "downtime_end": "07:00",   # Default overnight end (Now valid)
                "require_passcode": True,
                "notify_emails": ["parent1@example.com", "guardian@example.com"],
                "data_sharing_preference": False,
            },
             "example_same_day": { # Add another example if useful
                "downtime_enabled": True,
                "downtime_days": ["Sat", "Sun"],
                "downtime_start": "10:00",
                "downtime_end": "18:00",
                # ... other fields
            }
        }


# --- Schema for Reading Data ---
class ParentalSettingsRead(ParentalSettingsBase):
    id: str = Field(..., alias='_id', description="Unique identifier for the parental settings document.")

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = { # Example specific to Read (using valid overnight)
            "example": {
                "id": "6811a5b...",
                "block_violence": False,
                "block_inappropriate": True,
                "daily_limit_hours": "2",
                "asd_level": "medium",
                "downtime_enabled": True,
                "downtime_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                "downtime_start": "21:00",
                "downtime_end": "07:00", # Now valid example
                "require_passcode": True,
                "notify_emails": ["parent1@example.com", "guardian@example.com"],
                "data_sharing_preference": False,
            }
        }


# --- Schema for Updating Data ---
class ParentalSettingsUpdate(ParentalSettingsBase):
    # Inherits all fields from Base as optional for input AND inherits the validators
    pass

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": { # Example of updating to a same-day downtime
                "downtime_enabled": True,
                "downtime_start": "19:00",
                "downtime_end": "21:00",
                "daily_limit_hours": "3",
                "notify_emails": ["parent1@example.com"],
                "downtime_days": ["Sat", "Sun"]
            }
        }