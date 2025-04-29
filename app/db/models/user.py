# app/db/models/user.py
import re
import logging
from typing import Optional, List, Annotated, Any, Union # Added Union for clarity below
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, EmailStr, field_validator, model_validator, HttpUrl
# Assuming enums are defined correctly in .enums
from .enums import UserType, UserStatus, Gender

# Get logger instance
logger = logging.getLogger(__name__)

# --- Constants ---
# Basic regex for phone numbers: allows +, digits, spaces, hyphens, parentheses. Min 5, Max 20 chars overall.
PHONE_NUMBER_REGEX = r"^\+?[\d\s\-\(\)]{5,20}$" # Kept basic regex, advanced validation is optional

# --- User Document Model ---
class User(Document):
    """
    Represents a user in the Communify application, stored in the 'users' collection.
    Includes core details, profile information, and metadata.
    """

    # --- Core Identification & Credentials ---
    email: Annotated[
        EmailStr,
        Indexed(unique=True) # Ensures email is unique at the database level
    ] = Field(description="User's unique email address used for login.")

    # Use Annotated for consistency, though Field alone works too
    name: Annotated[
        str,
        Field(min_length=1, max_length=100)
    ] = Field(description="User's display name.")

    hashed_password: str = Field(description="Securely hashed user password using a strong algorithm (e.g., bcrypt, Argon2).")

    # --- Optional Profile Information ---
    phone_number: Optional[
        Annotated[str, Field(pattern=PHONE_NUMBER_REGEX, min_length=5, max_length=25)] # Basic pattern validation
    ] = Field(default=None, description="User's phone number (optional, basic format validation).")

    user_type: UserType = Field(
        default=UserType.PARENT, # Default to PARENT for new registrations via public endpoint
        description="Role of the user within the application (e.g., parent, admin)."
    )

    status: UserStatus = Field(
        default=UserStatus.ACTIVE,
        description="Current status of the user account (e.g., active, inactive, pending)."
    )

    # Constrained age using Annotated and Field constraints
    age: Optional[Annotated[int, Field(gt=0, lt=150)]] = Field(
        default=None,
        description="User's age (optional)."
    )

    gender: Optional[Gender] = Field(
        default=None,
        description="User's gender identity (optional)."
    )

    # Use HttpUrl for web URLs, allow fallback to str for other URIs (file://, data:, etc.)
    # Union type hint clarifies this intent.
    avatar_uri: Optional[Union[HttpUrl, str]] = Field(
        default=None,
        description="URI pointing to the user's avatar image (optional, can be web URL or other URI string)."
    )

    # --- App-Specific Data ---
    # Validate that favorite phrases are strings and not excessively long
    favorite_phrases: List[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list,
        description="List of user's saved favorite phrases (max 200 chars each)."
    )

    # --- Metadata & Status ---
    is_active: bool = Field(
        default=True,
        # index=True, # Explicit index defined in Settings class below
        description="Flag indicating if the user account can log in and use the system."
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # --- Beanie Settings ---
    class Settings:
        name = "users" # MongoDB collection name
        # Define indexes for commonly queried fields
        indexes = [
            # Unique index on 'email' is automatically created via Indexed(unique=True) above
            [("is_active", 1)], # Index for filtering by active status
            [("user_type", 1)], # Index for filtering by user type
            # Add other indexes as needed, e.g., [("status", 1)]
        ]

    # --- Hooks ---
    async def before_save(self):
        """Automatically update 'updated_at' timestamp before any save operation."""
        self.updated_at = datetime.now()
        # Log using ID if available (after first save), otherwise fallback to email
        user_identifier = str(self.id) if self.id else self.email
        logger.debug("Updating 'updated_at' for User %s", user_identifier) # type: ignore # May help linters with self.id potentially being None

    # --- Field Validators ---
    @field_validator('name', 'phone_number', mode='before')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Removes leading/trailing whitespace from name and phone number if they are strings."""
        if isinstance(v, str):
            return v.strip()
        return v

    # --- Advanced Phone Validation (Optional Enhancement) ---
    # Uncomment and install 'phonenumbers' library if needed.
    # @field_validator('phone_number')
    # @classmethod
    # def validate_phone_advanced(cls, v: Optional[str]) -> Optional[str]:
    #     """Performs advanced phone number validation using the 'phonenumbers' library."""
    #     if v is None: # Allow None
    #         return None
    #     v = v.strip() # Ensure stripped value is used
    #     if not v: # Allow empty string after stripping (treat as None conceptually)
    #          return None
    #     try:
    #         import phonenumbers # type: ignore
    #         # Parse the number. Region ('US', 'GB', etc.) can be specified if needed for numbers without country code.
    #         # Using None attempts international parsing.
    #         parsed_number = phonenumbers.parse(v, None)
    #         if not phonenumbers.is_valid_number(parsed_number):
    #             raise ValueError('Invalid phone number format or non-existent number.')
    #         # Optional: Format to E.164 standard before returning/saving
    #         # return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    #         return v # Return original (but validated) number for now
    #     except ImportError:
    #         logger.warning("Optional 'phonenumbers' library not installed. Skipping advanced phone validation for '%s'. Falling back to basic checks.", v)
    #         # Basic regex check (redundant if Field pattern exists, but safe fallback here)
    #         if not re.fullmatch(PHONE_NUMBER_REGEX, v):
    #              raise ValueError('Invalid basic phone number format provided.')
    #         return v
    #     except phonenumbers.NumberParseException as e:
    #         # More specific error for parsing failures
    #         raise ValueError(f'Invalid phone number: {e}') from e
    #     except Exception as e:
    #          # Catch unexpected errors during validation
    #          logger.error("Unexpected error during phone validation for '%s': %s", v, e, exc_info=True)
    #          raise ValueError('Could not validate phone number due to an unexpected error.')


    # --- Model Validators ---
    @model_validator(mode='after')
    def check_status_consistency(self) -> 'User':
        """
        Ensures the user's 'status' aligns with the 'is_active' flag.
        If 'is_active' is False, 'status' should not be ACTIVE.
        If 'is_active' is True, 'status' should ideally not be INACTIVE (corrects it).
        """
        user_identifier = str(self.id) if self.id else self.email
        if not self.is_active and self.status == UserStatus.ACTIVE:
            logger.warning(
                "User %s is marked as inactive (is_active=False) but status is ACTIVE. Automatically setting status to INACTIVE.",
                user_identifier
            )
            self.status = UserStatus.INACTIVE # Enforce consistency
        elif self.is_active and self.status == UserStatus.INACTIVE:
            # This case might occur if is_active is set True directly without changing status
            logger.info(
                "User %s is marked as active (is_active=True) but status is INACTIVE. Automatically setting status to ACTIVE.",
                 user_identifier
            )
            self.status = UserStatus.ACTIVE # Correct status to align with is_active
        # Note: Other statuses (like PENDING) might be valid whether is_active is True or False,
        # depending on application logic, so they are not modified here.
        return self

# --- Forward Reference Resolution ---
# No forward references (Links to models defined later in the file or other files)
# are used within the User model itself, so model_rebuild() is not needed here.