# app/api/v1/endpoints/auth.py
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from beanie.exceptions import DocumentNotFound
from pydantic import ValidationError

from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    verify_parental_passcode,
)
from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings
from app.db.models.enums import UserType, UserStatus, Gender
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from app.schemas.auth import (  # Assuming these are in passcode.py
    ParentalPasscodeVerifyRequest,
    ParentalPasscodeVerifyResponse,
    ParentalPasscodeSetRequest,
    ParentalPasscodeSetResponse,
    ParentalPasscodeRemoveRequest,
    ParentalPasscodeRemoveResponse,
    HasParentalPasscodeResponse,
)
from app.api.deps import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/token", response_model=Token, summary="Login for Access Token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    username = form_data.username
    logger.info(f"Login attempt for email: {username}")
    try:
        user = await User.find_one(User.email == username)
        if (
            not user
            or not user.hashed_password
            or not verify_password(form_data.password, user.hashed_password)
        ):
            logger.warning(
                f"Login failed for {username}: Invalid credentials or user not found."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active or user.status != UserStatus.ACTIVE:
            logger.warning(
                f"Login failed for {username}: User inactive (active: {user.is_active}, status: {user.status})."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive.",
            )

        access_token = create_access_token(subject=str(user.id))
        logger.info(f"Login successful for {user.email} (ID: {user.id}).")
        return Token(access_token=access_token, token_type="bearer")
    except Exception as e:
        logger.exception(f"Unexpected error during login for {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during login.",
        )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
)
async def register_user(user_in: UserCreate):
    logger.info(f"Registration attempt for email: {user_in.email}")
    existing_user = await User.find_one(User.email == user_in.email)
    if existing_user:
        logger.warning(f"Registration failed: Email '{user_in.email}' already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    try:
        hashed_password = get_password_hash(user_in.password)
    except ValueError as ve:
        logger.error(f"Password hashing failed for {user_in.email}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception(
            f"Password hashing failed unexpectedly for {user_in.email}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing registration data.",
        )

    user_data_to_create = user_in.model_dump(exclude={"password"})

    new_user_doc = User(
        **user_data_to_create, hashed_password=hashed_password, status=UserStatus.ACTIVE
    )

    inserted_user: Optional[User] = None
    try:
        inserted_user = await new_user_doc.save()
        if not inserted_user or not inserted_user.id:
            logger.critical(f"User save operation failed for {user_in.email}.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to finalize user creation.",
            )
        logger.info(f"User '{inserted_user.email}' created with ID: {inserted_user.id}")

        try:
            await ParentalSettings(user=inserted_user).save()
            await AppearanceSettings(user=inserted_user).save()
            logger.info(f"Default settings created for user ID: {inserted_user.id}")
        except Exception as settings_e:
            logger.error(
                f"Failed to create default settings for user {inserted_user.id}. Rolling back user. Error: {settings_e}",
                exc_info=True,
            )
            if inserted_user:
                await inserted_user.delete()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize user settings.",
            )

    except Exception as db_e:
        logger.exception(
            f"Database error during user registration for {user_in.email}: {db_e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred during registration.",
        )

    try:
        user_dict_for_validation = inserted_user.model_dump(
            mode="json",  # Converts ObjectId to str, datetime to ISO str, enums to values
            by_alias=True,  # Converts _id field of Beanie model to 'id' key in dict
            exclude={"hashed_password"},
        )
        logger.debug(
            f"--- DEBUG: Dictionary for UserRead validation (after model_dump by_alias=True, mode='json'): {user_dict_for_validation}"
        )
        user_response_object = UserRead.model_validate(user_dict_for_validation)

        logger.info(
            f"Registration successful for {inserted_user.email}. Response prepared."
        )
        logger.debug(
            f"--- DEBUG: Final UserRead object to be returned: {user_response_object.model_dump_json(indent=2)}"
        )
        return user_response_object

    except ValidationError as ve:
        logger.error(
            f"Pydantic validation error for UserRead, user {inserted_user.email}: {ve.errors(include_url=False)}"
        )
        logger.debug(
            f"--- DEBUG: Data that failed UserRead.model_validate: {user_dict_for_validation if 'user_dict_for_validation' in locals() else 'user_dict_for_validation not defined (pre-dump error?)'}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error preparing user response.",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error preparing UserRead response for {inserted_user.email}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error preparing user response.",
        )


@router.post(
    "/verify-parental-passcode",
    response_model=ParentalPasscodeVerifyResponse,
    summary="Verify Parental Passcode",
    tags=["Parental Controls"],
)
async def verify_parental_passcode_endpoint(
    request_data: ParentalPasscodeVerifyRequest,
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"Verifying parental passcode for user: {current_user.email}")
    parental_settings = await ParentalSettings.find_one(
        ParentalSettings.user.id == current_user.id
    )
    if not parental_settings:
        logger.warning(f"Parental settings not found for user: {current_user.email}.")
        return ParentalPasscodeVerifyResponse(
            success=False, message="Parental settings not configured."
        )
    if not parental_settings.hashed_parental_passcode:
        logger.warning(f"No parental passcode set for user: {current_user.email}")
        return ParentalPasscodeVerifyResponse(
            success=False, message="Parental passcode has not been set up."
        )

    if verify_parental_passcode(
        request_data.passcode, parental_settings.hashed_parental_passcode
    ):
        logger.info(f"Parental passcode verified for user: {current_user.email}")
        return ParentalPasscodeVerifyResponse(
            success=True, message="Passcode verified."
        )
    else:
        logger.warning(f"Incorrect parental passcode for user: {current_user.email}")
        return ParentalPasscodeVerifyResponse(
            success=False, message="Incorrect passcode."
        )


@router.get(
    "/has-parental-passcode",
    response_model=HasParentalPasscodeResponse,
    summary="Check Parental Passcode Status",
    tags=["Parental Controls"],
)
async def has_parental_passcode_endpoint(
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"Checking parental passcode status for user: {current_user.email}")
    parental_settings = await ParentalSettings.find_one(
        ParentalSettings.user.id == current_user.id
    )
    if not parental_settings:
        logger.warning(f"Parental settings not found for user: {current_user.email}.")
        return HasParentalPasscodeResponse(
            passcode_is_set=False, message="Parental settings not configured."
        )

    passcode_is_set = bool(parental_settings.hashed_parental_passcode)
    logger.info(
        f"Parental passcode for user {current_user.email} is_set: {passcode_is_set}"
    )
    return HasParentalPasscodeResponse(passcode_is_set=passcode_is_set)


@router.post(
    "/set-parental-passcode",
    response_model=ParentalPasscodeSetResponse,
    summary="Set/Update Parental Passcode",
    tags=["Parental Controls"],
)
async def set_parental_passcode_endpoint(
    request_data: ParentalPasscodeSetRequest,
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"Setting/updating parental passcode for user: {current_user.email}")
    parental_settings = await ParentalSettings.find_one(
        ParentalSettings.user.id == current_user.id
    )
    if not parental_settings:
        logger.error(
            f"Parental settings not found for user {current_user.email} during passcode set."
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Parental settings not found."
        )

    if parental_settings.hashed_parental_passcode and not request_data.current_passcode:
        logger.warning(
            f"Current passcode required to change existing passcode for user: {current_user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current passcode required."
        )
    if parental_settings.hashed_parental_passcode and not verify_parental_passcode(request_data.current_passcode, parental_settings.hashed_parental_passcode):  # type: ignore
        logger.warning(
            f"Incorrect current passcode during update for user: {current_user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current passcode.",
        )

    try:
        parental_settings.hashed_parental_passcode = get_password_hash(
            request_data.new_passcode
        )
    except ValueError as e:
        logger.error(
            f"Error hashing new parental passcode for {current_user.email}: {e}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await parental_settings.save()
    logger.info(f"Parental passcode set/updated for user: {current_user.email}")
    return ParentalPasscodeSetResponse(
        success=True, message="Parental passcode successfully set/updated."
    )


@router.post(
    "/remove-parental-passcode",
    response_model=ParentalPasscodeRemoveResponse,
    summary="Remove Parental Passcode",
    tags=["Parental Controls"],
)
async def remove_parental_passcode_endpoint(
    request_data: ParentalPasscodeRemoveRequest,
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"Removing parental passcode for user: {current_user.email}")
    parental_settings = await ParentalSettings.find_one(
        ParentalSettings.user.id == current_user.id
    )

    if not parental_settings or not parental_settings.hashed_parental_passcode:
        logger.warning(f"No parental passcode to remove for user: {current_user.email}")
        return ParentalPasscodeRemoveResponse(
            success=False, message="No parental passcode set."
        )

    if not verify_parental_passcode(
        request_data.current_passcode, parental_settings.hashed_parental_passcode
    ):
        logger.warning(
            f"Incorrect current passcode for removal for user: {current_user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current passcode.",
        )

    parental_settings.hashed_parental_passcode = None
    await parental_settings.save()
    logger.info(f"Parental passcode removed for user: {current_user.email}")
    return ParentalPasscodeRemoveResponse(
        success=True, message="Parental passcode removed."
    )
