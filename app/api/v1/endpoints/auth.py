# app/api/v1/endpoints/auth.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from beanie.exceptions import DocumentNotFound

# --- Core Imports ---
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings 

# --- Database Imports ---
from app.db.models.user import User
from app.db.models.settings import ParentalSettings # Import settings models to create defaults
from app.db.models.appearance_settings import AppearanceSettings
from app.db.models.enums import UserType, UserStatus # Import enums

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
    form_data: OAuth2PasswordRequestForm = Depends() # Uses form data (username=email, password)
):
    """
    Handles user login using the OAuth2 Password Flow.
    Verifies credentials and returns an access token upon success.
    """
    logger.info(f"Login attempt for username (email): {form_data.username}")
    try:
        # Find user by email (which is passed as 'username' in OAuth2 form)
        user = await User.find_one(User.email == form_data.username)

        # Check if user exists and password is correct
        if not user or not verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for email: {form_data.username} (Incorrect credentials)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user account is active
        if not user.is_active or user.status != UserStatus.ACTIVE:
            logger.warning(f"Failed login attempt for email: {form_data.username} (User inactive/status not active)")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive or has an invalid status."
            )

        # Create and return the access token
        access_token = create_access_token(subject=user.email)
        logger.info(f"Login successful, token generated for user: {user.email}")
        return Token(access_token=access_token, token_type="bearer")

    except DocumentNotFound:
        # This case is technically covered by `user is None` check above,
        # but catch it explicitly for robustness if find_one behavior changes.
         logger.warning(f"Failed login attempt: User not found in DB for email: {form_data.username}")
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password", # Keep detail generic
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # Catch unexpected errors during login process
        logger.exception(f"Unexpected error during login for {form_data.username}: {e}") # Use logger.exception for traceback
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
    description=f"Creates a new user account with the default role '{UserType.PARENT.value}'.",
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
        logger.error("Password hashing failed during registration: %s", e, exc_info=True)
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
        # Other fields like phone, age, gender will be None/default unless added to UserCreate
    )

    # --- Insert User and Default Settings (in a "transactional" manner) ---
    inserted_user = None # Initialize to None
    try:
        # Insert the user
        inserted_user = await user.insert()
        if not inserted_user or not inserted_user.id:
             logger.error("Database insert succeeded but user object/ID is missing for email %s", user_in.email)
             # This is a critical failure state
             raise HTTPException(status_code=500, detail="Failed to finalize user creation.")
        logger.info(f"User '{inserted_user.email}' created successfully with ID: {inserted_user.id}")

        # Create default settings linked to the user
        try:
            default_parental = ParentalSettings(user=inserted_user) # type: ignore Beanie handles Link assignment
            await default_parental.insert()
            logger.info(f"Created default ParentalSettings for user {inserted_user.id}")

            default_appearance = AppearanceSettings(user=inserted_user) # type: ignore Beanie handles Link assignment
            await default_appearance.insert()
            logger.info(f"Created default AppearanceSettings for user {inserted_user.id}")

        except Exception as settings_e:
            # If settings creation fails, roll back user creation for consistency
            logger.error("Failed to create default settings for user %s, rolling back user creation: %s", inserted_user.id, settings_e, exc_info=True)
            await inserted_user.delete() # Attempt to delete the partially created user
            raise HTTPException(status_code=500, detail="Failed to initialize user settings after registration.")

    except Exception as e:
        # Catch potential database errors during user insert itself
        logger.error("Database error during user insertion for email %s: %s", user_in.email, e, exc_info=True)
        # Check if user was partially inserted and try to clean up if necessary
        if inserted_user and inserted_user.id:
             logger.warning("Attempting cleanup for partially inserted user %s", inserted_user.id)
             await inserted_user.delete()
        raise HTTPException(status_code=500, detail="Database error during user registration.")


    # --- Prepare and Return Response ---
    # Ensure the ID is converted to string for the Pydantic model
    user_read_data = {
        "id": str(inserted_user.id),
        "email": inserted_user.email,
        "name": inserted_user.name,
        "avatar_uri": inserted_user.avatar_uri,
        "is_active": inserted_user.is_active,
        "user_type": inserted_user.user_type,
        "created_at": inserted_user.created_at,
        "updated_at": inserted_user.updated_at
    }
    return UserRead(**user_read_data)