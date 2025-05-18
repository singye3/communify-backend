# app/api/v1/endpoints/users.py
import logging
from typing import Any, Dict  # Added Dict
from fastapi import APIRouter, Depends, HTTPException, status

# from fastapi import Response # Not used in this version

from app.db.models.user import User
from app.db.models.enums import (
    UserStatus,
    UserType,
    Gender,
)  # Import enums used for conversion
from app.schemas.user import UserRead, UserUpdate, UserPasswordUpdate
from app.api.deps import get_current_active_user
from app.core.security import verify_password, get_password_hash

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================
# CURRENT USER ENDPOINTS (/me)
# ============================


def _prepare_user_read_data(user_model: User) -> Dict[str, Any]:
    """
    Helper function to convert a User model instance to a dictionary
    suitable for UserRead Pydantic validation, handling ObjectId and Enums.
    """
    if not user_model:
        # This should ideally not be reached if called with a valid user model
        logger.error("Attempted to prepare UserRead data from a None user_model.")
        raise ValueError("Cannot prepare response data from a null user model.")

    response_data = user_model.model_dump(
        exclude={
            "hashed_password",
            "status",
        }  # Exclude fields not in UserRead or sensitive
        # 'status' is often an internal field, 'is_active' is public
    )
    response_data["id"] = str(user_model.id)

    if "user_type" in response_data and isinstance(
        response_data["user_type"], UserType
    ):
        response_data["user_type"] = response_data["user_type"].value
    if (
        "gender" in response_data
        and response_data["gender"]
        and isinstance(response_data["gender"], Gender)
    ):
        response_data["gender"] = response_data["gender"].value
    # Add other enum conversions here if they are part of UserRead and your User model

    return response_data


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get Current User",
    description="Retrieves the profile details for the currently authenticated user.",
    tags=["Users - Current User (/me)"],
)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Fetches and returns the logged-in user's data."""
    logger.debug(f"Fetching profile for user: {current_user.email}")
    try:
        prepared_data = _prepare_user_read_data(current_user)
        return UserRead.model_validate(prepared_data)
    except Exception:
        logger.exception(
            f"Error validating/preparing user data for {current_user.email}"
        )
        raise HTTPException(
            status_code=500, detail="Internal server error processing user data."
        )


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update Current User Profile",
    description="Allows the authenticated user to update specific profile fields like name, age, and gender.",
    tags=["Users - Current User (/me)"],
)
async def update_user_me(
    user_in: UserUpdate, current_user: User = Depends(get_current_active_user)
):
    """Updates profile fields for the logged-in user."""
    logger.info(f"Attempting profile update for user: {current_user.email}")
    update_data = user_in.model_dump(exclude_unset=True)

    if not update_data:
        logger.info(
            f"Update request for user '{current_user.email}' had no data to update."
        )
        prepared_data = _prepare_user_read_data(current_user)
        return UserRead.model_validate(prepared_data)

    updated_fields_count = 0
    for field, value in update_data.items():
        if hasattr(current_user, field):  # UserUpdate schema should ensure valid fields
            if getattr(current_user, field) != value:
                setattr(current_user, field, value)
                updated_fields_count += 1
                # logger.debug(f"Staged update for '{current_user.email}': {field} to {value}")
        # else: # Should not be reached if UserUpdate is well-defined
        # logger.warning(f"Attempted to update non-existent field '{field}' for user '{current_user.email}'.")

    if updated_fields_count > 0:
        try:
            await current_user.save()
            logger.info(
                f"Profile updated ({updated_fields_count} fields) for {current_user.email}."
            )
        except Exception:
            logger.exception(f"DB error saving profile update for {current_user.email}")
            raise HTTPException(
                status_code=500, detail="Could not save profile changes."
            )
    else:
        logger.info(
            f"No actual changes for user '{current_user.email}'. No save performed."
        )

    try:
        prepared_data = _prepare_user_read_data(current_user)
        return UserRead.model_validate(prepared_data)
    except Exception:
        logger.exception(
            f"Error validating/preparing updated user data for {current_user.email}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error processing updated user data.",
        )


@router.put(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update Current User Password",
    description="Allows the authenticated user to change their own password after verifying the current one.",
    tags=["Users - Current User (/me)"],
    responses={
        204: {"description": "Password updated successfully"},
        400: {"description": "Incorrect current password"},
        422: {"description": "Validation error in input data"},
    },
)
async def update_user_password(
    password_in: UserPasswordUpdate,
    current_user: User = Depends(get_current_active_user),
) -> None:  # Return type is None for 204
    """Handles secure password change for the logged-in user."""
    logger.info(f"Password change attempt for user: {current_user.email}")

    if not verify_password(password_in.current_password, current_user.hashed_password):
        logger.warning(
            f"Password change failed for '{current_user.email}': Incorrect current password."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password.",
        )

    try:
        new_hashed_password = get_password_hash(password_in.new_password)
    except Exception:
        logger.exception(f"Password hashing failed for update: {current_user.email}")
        raise HTTPException(status_code=500, detail="Error processing new password.")

    try:
        current_user.hashed_password = new_hashed_password
        await current_user.save()
        logger.info(f"Password updated successfully for {current_user.email}.")
        # For 204, FastAPI handles returning no content if the function returns None
    except Exception:
        logger.exception(f"DB error saving new password for {current_user.email}")
        raise HTTPException(status_code=500, detail="Could not update password.")
    return None  # Explicitly return None for 204


@router.post(
    "/me/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate Current User Account",
    description="Allows the authenticated user to deactivate their own account. This is reversible by an administrator.",
    tags=["Users - Current User (/me)"],
    responses={
        204: {"description": "Account deactivated successfully"},
    },
)
async def deactivate_user_me(
    current_user: User = Depends(get_current_active_user),
) -> None:  # Return type is None for 204
    """Sets the user's account status to inactive."""
    logger.warning(f"User '{current_user.email}' requested self-deactivation.")

    if not current_user.is_active and current_user.status == UserStatus.INACTIVE:
        logger.info(
            f"User '{current_user.email}' is already inactive. No action taken."
        )
        return None

    try:
        current_user.is_active = False
        current_user.status = UserStatus.INACTIVE  # Ensure status aligns with is_active
        await current_user.save()
        logger.info(f"User account '{current_user.email}' deactivated successfully.")
    except Exception:
        logger.exception(f"DB error deactivating account for {current_user.email}")
        raise HTTPException(status_code=500, detail="Could not deactivate account.")
    return None  # Explicitly return None for 204
