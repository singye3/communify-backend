# app/api/v1/endpoints/auth.py
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from beanie.exceptions import DocumentNotFound # Keep for explicit catch if desired

# --- Core Imports ---
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings

# --- Database Imports ---
from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings
from app.db.models.enums import UserType, UserStatus

# --- Schema Imports ---
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead

# --- Get Logger ---
logger = logging.getLogger(__name__)

# --- API Router ---
router = APIRouter()

# ============================
# LOGIN ENDPOINT
# ============================
@router.post(
    "/token",
    response_model=Token,
    summary="Login for Access Token",
    description="Authenticate using email and password to receive a JWT Bearer token.",
    tags=["Authentication"]
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Handles user login using the OAuth2 Password Flow.
    Verifies credentials and returns an access token upon success.
    """
    username = form_data.username # Equivalent to email in this context
    logger.info(f"Login attempt for username (email): {username}")
    try:
        user = await User.find_one(User.email == username)

        # Combine checks for security: user exists AND password matches
        if not user or not verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for email: {username} (Incorrect credentials or user not found)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user account is active and has the correct status
        if not user.is_active or user.status != UserStatus.ACTIVE:
            logger.warning(f"Failed login attempt for email: {username} (User inactive or invalid status: is_active={user.is_active}, status={user.status})")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, # Or 401/403 depending on desired UX
                detail="User account is inactive or not permitted to login."
            )

        # Create and return the access token
        access_token = create_access_token(subject=user.email)
        logger.info(f"Login successful, token generated for user: {user.email}")
        return Token(access_token=access_token, token_type="bearer")

    except DocumentNotFound:
        # This catch block is technically redundant due to `if not user` check,
        # but provides explicit handling if find_one behavior ever changes.
         logger.warning(f"Failed login attempt (DocumentNotFound): User not found in DB for email: {username}")
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password", # Keep detail generic for security
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # Catch unexpected errors during the login process
        logger.exception(f"Unexpected error during login for {username}:") # logger.exception includes traceback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during login."
        )

# ============================
# REGISTRATION ENDPOINT
# ============================
@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description=f"Creates a new user account with the default role '{UserType.PARENT.value}'. Initializes default settings.",
    tags=["Authentication"]
)
async def register_user(
    user_in: UserCreate # Input validated by Pydantic schema
):
    """
    Handles public user registration. Checks for existing email,
    hashes password, creates the user, initializes default settings,
    and returns the created user data.
    """
    logger.info(f"Registration attempt for email: {user_in.email}")

    # --- Check for existing user ---
    existing_user = await User.find_one(User.email == user_in.email)
    if existing_user:
        logger.warning(f"Registration failed: Email '{user_in.email}' already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    # --- Hash password ---
    try:
        hashed_password = get_password_hash(user_in.password)
    except Exception as e:
        logger.exception("Password hashing failed during registration for email %s:", user_in.email)
        raise HTTPException(status_code=500, detail="Error processing registration data.")

    # --- Create User Document ---
    # Public registration defaults to PARENT type and ACTIVE status
    user = User(
        email=user_in.email,
        name=user_in.name,
        hashed_password=hashed_password,
        user_type=UserType.PARENT, # Default type for public registration
        status=UserStatus.ACTIVE,
        is_active=True
    )

    # --- Insert User and Default Settings ---
    # NOTE: User creation and default settings creation are not atomic.
    # Manual rollback is implemented below if settings creation fails.
    # Consider MongoDB transactions for stricter consistency guarantees if needed.
    inserted_user: Optional[User] = None # Initialize to None
    try:
        # 1. Insert the user
        inserted_user = await user.insert()
        if not inserted_user or not inserted_user.id:
             # This is a critical failure state, should ideally not happen if insert doesn't raise error
             logger.critical("CRITICAL: Database insert reported success but user object/ID is missing for email %s", user_in.email)
             raise HTTPException(status_code=500, detail="Failed to finalize user creation after insert.")
        logger.info(f"User '{inserted_user.email}' created successfully with ID: {inserted_user.id}")

        # 2. Create default settings linked to the user
        try:
            # Use Link reference correctly, type ignore for static analysis
            default_parental = ParentalSettings(user=inserted_user) # type: ignore
            await default_parental.insert()
            logger.info(f"Created default ParentalSettings for user {inserted_user.id}")

            default_appearance = AppearanceSettings(user=inserted_user) # type: ignore
            await default_appearance.insert()
            logger.info(f"Created default AppearanceSettings for user {inserted_user.id}")

        except Exception as settings_e:
            # If ANY settings creation fails, roll back user creation for consistency
            logger.error(
                "Failed to create default settings for user %s, initiating rollback of user creation: %s",
                inserted_user.id, settings_e, exc_info=True
            )
            await inserted_user.delete() # Attempt to delete the partially created user
            logger.warning(f"Successfully rolled back creation of user {inserted_user.id} due to settings failure.")
            # Raise exception to signal failure of the registration process
            raise HTTPException(status_code=500, detail="Failed to initialize user settings after registration. User creation was rolled back.")

    except Exception as e:
        # Catch potential database errors during user insert itself, or other unexpected errors
        logger.exception("Error during user registration process for email %s:", user_in.email)
        # Check if user object exists from a partial success before settings failure
        if inserted_user and hasattr(inserted_user, 'delete') and inserted_user.id:
             logger.warning("Attempting cleanup for potentially partially inserted user %s", inserted_user.id)
             # Double-check existence before deleting again in case delete was already called in inner block
             check_user = await User.get(inserted_user.id)
             if check_user:
                 await inserted_user.delete()
        # Raise a generic error for the client
        raise HTTPException(status_code=500, detail="Database error during user registration.")


    # --- Prepare and Return Response ---
    # Ensure the ID is converted to string for the Pydantic model
    user_read_data = {
        "id": str(inserted_user.id),
        "email": inserted_user.email,
        "name": inserted_user.name,
        "avatar_uri": str(inserted_user.avatar_uri) if inserted_user.avatar_uri else None, # Handle potential HttpUrl
        "is_active": inserted_user.is_active,
        "user_type": inserted_user.user_type,
        "created_at": inserted_user.created_at,
        "updated_at": inserted_user.updated_at
    }
    # Alternative: return UserRead.model_validate(inserted_user)
    return UserRead(**user_read_data)