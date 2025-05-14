# app/api/v1/endpoints/auth.py
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from beanie.exceptions import DocumentNotFound
from pydantic import ValidationError # For catching Pydantic specific validation errors

# Security utilities
from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    verify_parental_passcode
)

# Database Models
from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings
from app.db.models.enums import UserType, UserStatus, Gender

# Pydantic Schemas
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from app.schemas.auth import (
    ParentalPasscodeVerifyRequest,
    ParentalPasscodeVerifyResponse
)

from app.api.deps import get_current_active_user

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
    username = form_data.username
    logger.info(f"Login attempt for email: {username}")
    try:
        user = await User.find_one(User.email == username)
        if not user:
            logger.warning(f"Login failed for {username}: User not found.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
        if not user.hashed_password:
             logger.error(f"CRITICAL: User {username} found but has no hashed_password set.")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Account configuration error.")
        if not verify_password(form_data.password, user.hashed_password):
            logger.warning(f"Failed login for {username}: Incorrect password.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
        if not user.is_active or user.status != UserStatus.ACTIVE:
            logger.warning(f"Failed login for {username}: User inactive/invalid status (active: {user.is_active}, status: {user.status}).")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account is inactive or not permitted to login.")
        access_token = create_access_token(subject=user.email)
        logger.info(f"Login successful for {user.email}.")
        return Token(access_token=access_token, token_type="bearer")
    except DocumentNotFound:
        logger.warning(f"Login failed for {username}: User not found in DB (DocumentNotFound).")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    except Exception:
        logger.exception(f"Unexpected error during login for {username}.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred during login.")


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description=f"Creates a new user account with default role '{UserType.PARENT.value}'. Initializes default settings.",
    tags=["Authentication"]
)
async def register_user(user_in: UserCreate):
    logger.info(f"Registration attempt for email: {user_in.email}")
    existing_user = await User.find_one(User.email == user_in.email)
    if existing_user:
        logger.warning(f"Registration failed: Email '{user_in.email}' already exists.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists.")
    try:
        hashed_password = get_password_hash(user_in.password)
        logger.debug(f"Password hashed for {user_in.email}.")
    except ValueError as ve: # Catch specific error from get_password_hash for empty password
        logger.error(f"Password hashing failed for {user_in.email}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception:
        logger.exception(f"Password hashing failed for {user_in.email}.")
        raise HTTPException(status_code=500, detail="Error processing registration data.")

    user_data_for_db = user_in.model_dump(exclude={"password"})
    new_user_doc = User(**user_data_for_db, hashed_password=hashed_password, user_type=UserType.PARENT, status=UserStatus.ACTIVE, is_active=True)
    inserted_user: Optional[User] = None
    try:
        inserted_user = await new_user_doc.insert() # type: ignore
        if not inserted_user or not inserted_user.id:
            logger.critical(f"CRITICAL: User insert operation did not return valid user or ID for {user_in.email}.")
            raise HTTPException(status_code=500, detail="Failed to finalize user creation.")
        logger.info(f"User '{inserted_user.email}' created with ID: {inserted_user.id}")
        try:
            await ParentalSettings(user=inserted_user).insert() # type: ignore
            logger.info(f"Default ParentalSettings created for user ID: {inserted_user.id}")
            await AppearanceSettings(user=inserted_user).insert() # type: ignore
            logger.info(f"Default AppearanceSettings created for user ID: {inserted_user.id}")
        except Exception as settings_e:
            logger.error(f"Failed to create default settings for user {inserted_user.id}. Rolling back user: {settings_e}", exc_info=True)
            if inserted_user and inserted_user.id: await inserted_user.delete()
            logger.warning(f"Rolled back user {inserted_user.id} due to settings creation failure.")
            raise HTTPException(status_code=500, detail="Failed to initialize user settings. Registration rolled back.")
    except Exception as db_e:
        logger.exception(f"Database error during user registration for {user_in.email}: {db_e}")
        if inserted_user and inserted_user.id:
            logger.warning(f"Attempting cleanup for partially inserted user {inserted_user.id} due to broader DB error.")
            user_to_delete = await User.get(inserted_user.id)
            if user_to_delete: await user_to_delete.delete()
        raise HTTPException(status_code=500, detail="A database error occurred during registration.")

    logger.info(f"Registration successful for {inserted_user.email}, preparing response.")
    try:
        # Prepare dictionary for UserRead validation
        user_dict_for_response: Dict[str, Any] = inserted_user.model_dump(exclude={'hashed_password'})
        
        # Ensure 'id' is string
        user_dict_for_response['id'] = str(inserted_user.id)

        # Convert enums to their string values if UserRead expects strings
        # (Pydantic's from_attributes with use_enum_values might handle this, but explicit is safer)
        if 'user_type' in user_dict_for_response and isinstance(user_dict_for_response.get('user_type'), UserType):
            user_dict_for_response['user_type'] = user_dict_for_response['user_type'].value
        if 'gender' in user_dict_for_response and user_dict_for_response.get('gender') and isinstance(user_dict_for_response.get('gender'), Gender):
            user_dict_for_response['gender'] = user_dict_for_response['gender'].value
        # Assuming UserRead doesn't include 'status', if it does, convert it too.

        return UserRead.model_validate(user_dict_for_response)
    except ValidationError as ve: # Catch Pydantic specific validation error
        logger.error(f"Pydantic validation error for UserRead with data from user {inserted_user.email}: {ve.errors()}", exc_info=True)
        logger.debug(f"Data passed to UserRead.model_validate: {user_dict_for_response if 'user_dict_for_response' in locals() else 'user_dict_for_response not defined'}")
        raise HTTPException(status_code=500, detail="Error preparing user response data after registration.")
    except Exception as e: # Catch other unexpected errors
        logger.error(f"Unexpected error preparing UserRead response for {inserted_user.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error preparing user response data after registration.")


# --- Endpoint for Parental Passcode Verification ---
@router.post(
    "/verify-parental-passcode",
    response_model=ParentalPasscodeVerifyResponse,
    summary="Verify Parental Passcode",
    description="Verifies the provided parental passcode for the authenticated user.",
    tags=["Authentication", "Parental Controls"]
)
async def verify_parental_passcode_endpoint(
    request_data: ParentalPasscodeVerifyRequest,
    current_user: User = Depends(get_current_active_user)
):
    logger.info(f"Attempting to verify parental passcode for user: {current_user.email}")
    parental_settings: Optional[ParentalSettings] = await ParentalSettings.find_one(
        ParentalSettings.user.id == current_user.id # type: ignore
    )
    if not parental_settings:
        logger.warning(f"Parental settings not found for user: {current_user.email}. Cannot verify passcode.")
        return ParentalPasscodeVerifyResponse(success=False, message="Parental settings not configured for this account.")
    if not parental_settings.hashed_parental_passcode: # type: ignore
        logger.warning(f"No parental passcode has been set up for user: {current_user.email}")
        return ParentalPasscodeVerifyResponse(success=False, message="Parental passcode has not been set up.")
    is_correct = verify_parental_passcode(
        plain_passcode=request_data.passcode,
        hashed_passcode=parental_settings.hashed_parental_passcode # type: ignore
    )
    if is_correct:
        logger.info(f"Parental passcode verified successfully for user: {current_user.email}")
        return ParentalPasscodeVerifyResponse(success=True, message="Passcode verified successfully.")
    else:
        logger.warning(f"Incorrect parental passcode attempt for user: {current_user.email}")
        return ParentalPasscodeVerifyResponse(success=False, message="Incorrect passcode provided.")