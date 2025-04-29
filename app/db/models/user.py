# app/db/models/user.py
import re
import logging
from typing import Optional, List, Annotated, Any
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, EmailStr, field_validator, model_validator, HttpUrl
from .enums import UserType, UserStatus, Gender

# Get logger instance
logger = logging.getLogger(__name__)

# --- Constants ---
PHONE_NUMBER_REGEX = r"^\+?[\d\s\-\(\)]{5,20}$"

# --- User Document Model ---
class User(Document):
    """
    Represents a user in the Communify application, stored in the 'users' collection.
    Includes core details, profile information, and metadata.
    """

    # --- Core Identification & Credentials ---
    email: Annotated[
        EmailStr,
        Indexed(unique=True) 
    ] = Field(description="User's unique email address used for login.")

    name: Annotated[
        str,
        Field(min_length=1, max_length=100, description="User's display name.")
    ]

    hashed_password: str = Field(description="Securely hashed user password.")

    # --- Optional Profile Information ---
    phone_number: Optional[
        Annotated[str, Field(pattern=PHONE_NUMBER_REGEX, min_length=5, max_length=25)] # Use regex pattern
    ] = Field(default=None, description="User's phone number (optional, basic format validation).")

    user_type: UserType = Field(
        default=UserType.PARENT, # Default to PARENT for new registrations via public endpoint
        description="Role of the user within the application."
    )

    status: UserStatus = Field(
        default=UserStatus.ACTIVE,
        description="Current status of the user account."
    )

    # Constrained age (e.g., > 0)
    age: Optional[Annotated[int, Field(gt=0, lt=150)]] = Field(
        default=None,
        description="User's age (optional)."
    )

    gender: Optional[Gender] = Field(
        default=None,
        description="User's gender identity (optional)."
    )

    # Use HttpUrl type for better validation if URIs are expected to be web URLs
    avatar_uri: Optional[HttpUrl | str] = Field( # Allow standard strings too for file:// etc.
        default=None,
        description="URI pointing to the user's avatar image (optional)."
    )

    # --- App-Specific Data ---
    # Validate that favorite phrases are strings and not excessively long
    favorite_phrases: List[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list,
        description="List of user's saved favorite phrases."
    )

    # --- Metadata & Status ---
    is_active: bool = Field(
        default=True,
        index=True, # Indexed for efficiently querying active users
        description="Flag indicating if the user account can log in and use the system."
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # --- Beanie Settings ---
    class Settings:
        name = "users" 
        indexes = [
            [("is_active", 1)],
            [("user_type", 1)],
        ]

    # --- Hooks ---
    async def before_save(self):
        """Automatically update 'updated_at' timestamp before any save operation."""
        self.updated_at = datetime.now()
        logger.debug("Updating 'updated_at' for User %s", self.id or self.email)

    # --- Field Validators ---
    @field_validator('name', 'phone_number', mode='before')
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            return v.strip()
        return v

    # Advanced phone validation (optional, requires 'phonenumbers' library)
    # @field_validator('phone_number')
    # @classmethod
    # def validate_phone_advanced(cls, v: Optional[str]) -> Optional[str]:
    #     if v is None:
    #         return None
    #     try:
    #         import phonenumbers # type: ignore
    #         # Assuming default region for parsing if no country code prefix, adjust as needed
    #         # Example: 'US' - requires installing phonenumbers[phonenumberslite] or full version
    #         parsed_number = phonenumbers.parse(v, None) # Set region if needed
    #         if not phonenumbers.is_valid_number(parsed_number):
    #             raise ValueError('Invalid phone number format or non-existent number.')
    #         # Optional: Format to a standard format like E.164
    #         # return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    #         return v # Return original valid number for now
    #     except ImportError:
    #         logger.warning("Phonenumbers library not installed, skipping advanced phone validation.")
    #         # Fall back to regex validation (if pattern is set on Field) or basic checks
    #         if not re.fullmatch(PHONE_NUMBER_REGEX, v.strip()):
    #              raise ValueError('Invalid basic phone number format provided.')
    #         return v
    #     except phonenumbers.NumberParseException as e:
    #         raise ValueError(f'Invalid phone number: {e}') from e
    #     except Exception as e:
    #          logger.error("Unexpected error during phone validation: %s", e, exc_info=True)
    #          raise ValueError('Could not validate phone number.')


    # --- Model Validators ---
    @model_validator(mode='after')
    def check_status_consistency(self) -> 'User':
        """Ensures user status aligns with is_active flag."""
        if not self.is_active and self.status == UserStatus.ACTIVE:
            logger.warning(
                "User %s marked as inactive but status is ACTIVE. Setting status to INACTIVE.",
                self.id or self.email
            )
            self.status = UserStatus.INACTIVE
        elif self.is_active and self.status == UserStatus.INACTIVE:
            logger.info(
                "User %s marked as active but status is INACTIVE. Setting status to ACTIVE.",
                 self.id or self.email
            )
            self.status = UserStatus.ACTIVE
        return self

# --- Forward Reference Resolution ---
# Not needed in this file as User does not Link to other models defined *after* it.
# If User linked to e.g., Role model defined below, you would need:
# from .role import Role # Assuming Role model exists
# User.model_rebuild()