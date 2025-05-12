# app/api/v1/endpoints/auth.py
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from beanie.exceptions import DocumentNotFound

from app.core.security import create_access_token, verify_password, get_password_hash

from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings
from app.db.models.enums import UserType, UserStatus, Gender

from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/token",
    response_model=Token,
    summary="Login for Access Token",
    description="Authenticate using email and password to receive a JWT Bearer token.",
    tags=["Authentication"]
)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Handles user login. Verifies credentials and returns an access token.
    """
    username = form_data.username  # Email
    logger.info(f"Login attempt for email: {username}")
    try:
        user = await User.find_one(User.email == username)

        if not user or not verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Failed login for {username}: Incorrect credentials or user not found.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active or user.status != UserStatus.ACTIVE:
            logger.warning(f"Failed login for {username}: User inactive/invalid status (active: {user.is_active}, status: {user.status}).")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive or not permitted to login."
            )

        access_token = create_access_token(subject=user.email)
        logger.info(f"Login successful for {user.email}.")
        return Token(access_token=access_token, token_type="bearer")

    except DocumentNotFound: # Should be caught by `if not user`
        logger.warning(f"Login failed for {username}: User not found in DB (DocumentNotFound).")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        logger.exception(f"Unexpected error during login for {username}.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during login."
        )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description=f"Creates a new user account with default role '{UserType.PARENT.value}'. Initializes default settings.",
    tags=["Authentication"]
)
async def register_user(user_in: UserCreate):
    """
    Handles public user registration.
    Creates user, initializes default settings, and returns created user data.
    """
    logger.info(f"Registration attempt for email: {user_in.email}")

    if await User.find_one(User.email == user_in.email):
        logger.warning(f"Registration failed: Email '{user_in.email}' already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    try:
        hashed_password = get_password_hash(user_in.password)
        logger.debug(f"Password hashed for {user_in.email}.")
    except Exception:
        logger.exception(f"Password hashing failed for {user_in.email}.")
        raise HTTPException(status_code=500, detail="Error processing registration data.")

    user_data_for_db = user_in.model_dump(exclude={"password"})
    user = User(
        **user_data_for_db,
        hashed_password=hashed_password,
        user_type=UserType.PARENT,
        status=UserStatus.ACTIVE,
        is_active=True,
    )

    inserted_user: Optional[User] = None
    try:
        inserted_user = await user.insert()
        if not inserted_user or not inserted_user.id:
            logger.critical(f"CRITICAL: User insert success but object/ID missing for {user_in.email}.")
            raise HTTPException(status_code=500, detail="Failed to finalize user creation.")
        logger.info(f"User '{inserted_user.email}' created with ID: {inserted_user.id}")

        try:
            await ParentalSettings(user=inserted_user).insert()
            logger.info(f"Default ParentalSettings created for user {inserted_user.id}.")
            await AppearanceSettings(user=inserted_user).insert()
            logger.info(f"Default AppearanceSettings created for user {inserted_user.id}.")
        except Exception as settings_e:
            logger.error(f"Failed to create default settings for user {inserted_user.id}, rolling back user: {settings_e}", exc_info=True)
            await inserted_user.delete()
            logger.warning(f"Rolled back user {inserted_user.id} due to settings failure.")
            raise HTTPException(status_code=500, detail="Failed to initialize user settings. Registration rolled back.")

    except Exception:
        logger.exception(f"Error during user registration for {user_in.email}.")
        if inserted_user and inserted_user.id: # Check if inserted_user exists and has an ID
            logger.warning(f"Attempting cleanup for partially inserted user {inserted_user.id}.")
            # Verify before delete to avoid errors if already deleted or rollback occurred
            user_to_delete = await User.get(inserted_user.id)
            if user_to_delete:
                await user_to_delete.delete() # Use the fetched object for delete
                logger.info(f"Cleanup successful for user {inserted_user.id}.")
            else:
                logger.info(f"User {inserted_user.id} already cleaned up or not found for cleanup.")
        raise HTTPException(status_code=500, detail="Database error during user registration.")

    # --- Prepare and Return Response ---
    # Explicitly convert ObjectId and Enums to strings/values for Pydantic validation
    # if UserRead schema expects them as such.
    if not inserted_user: # Should be caught above, but defensive check
        logger.error("inserted_user is None before returning response. This should not happen.")
        raise HTTPException(status_code=500, detail="User data unavailable after creation.")

    logger.info(f"Registration successful for {inserted_user.email}, preparing response.")

    # Create a dictionary from the Beanie model, then make necessary conversions
    response_data: Dict[str, Any] = inserted_user.model_dump(
        exclude={'hashed_password'} # Exclude sensitive fields not in UserRead
    )
    response_data['id'] = str(inserted_user.id) # Convert ObjectId to string

    # Convert enums to their string values if UserRead expects strings
    if 'user_type' in response_data and isinstance(response_data['user_type'], UserType):
        response_data['user_type'] = response_data['user_type'].value
    if 'gender' in response_data and response_data['gender'] and isinstance(response_data['gender'], Gender):
        response_data['gender'] = response_data['gender'].value
    # Note: 'status' is not typically part of UserRead for basic registration response.
    # If it is, and it's an enum, convert it too:
    # if 'status' in response_data and isinstance(response_data['status'], UserStatus):
    #     response_data['status'] = response_data['status'].value


    try:
        # Validate the prepared dictionary against the UserRead schema
        return UserRead.model_validate(response_data)
    except Exception as e:
        # Log the data that failed validation for easier debugging
        logger.error(f"Pydantic validation error for UserRead with data {response_data}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error preparing user response data.")