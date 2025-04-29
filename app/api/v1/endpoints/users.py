# app/api/v1/endpoints/users.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status # Removed Body as not directly used
from typing import Optional

# --- App Imports ---
from app.db.models.user import User
from app.db.models.enums import UserStatus
# Assuming UserPasswordUpdate is defined in app.schemas.user
from app.schemas.user import UserRead, UserUpdate, UserPasswordUpdate
from app.api.deps import get_current_active_user
from app.core.security import verify_password, get_password_hash

# --- Get Logger ---
logger = logging.getLogger(__name__)

# --- API Router ---
router = APIRouter()

# ============================
# CURRENT USER ENDPOINTS (/me)
# ============================

@router.get(
    "/me",
    response_model=UserRead,
    summary="Get Current User",
    description="Retrieves the profile details for the currently authenticated user.",
    tags=["Users - Current User (/me)"] # More specific tag
)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """Fetches and returns the logged-in user's data."""
    logger.debug(f"Fetching profile for user: {current_user.email}")
    try:
        # Dependency already provides the user object. Check for essential attributes.
        if not current_user.id:
            logger.error(f"User object for '{current_user.email}' obtained from dependency is missing 'id' attribute.")
            raise HTTPException(status_code=500, detail="Internal server error: User data incomplete.")

        # Prepare response data manually or use model_validate
        user_read_data = {
            "id": str(current_user.id),
            "email": current_user.email,
            "name": current_user.name,
            # Ensure HttpUrl is stringified if necessary (Pydantic v2 usually handles this)
            "avatar_uri": str(current_user.avatar_uri) if current_user.avatar_uri else None,
            "is_active": current_user.is_active,
            "user_type": current_user.user_type,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at
        }
        logger.debug(f"Successfully prepared read data for user: {current_user.email}")
        # Alternative: return UserRead.model_validate(current_user)
        return UserRead(**user_read_data)

    except Exception as e:
        logger.exception(f"Unexpected error fetching profile for user {current_user.email}:")
        raise HTTPException(status_code=500, detail="An error occurred while fetching user profile.")


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update Current User Profile",
    description="Allows the authenticated user to update specific profile fields like name and avatar URI.",
    tags=["Users - Current User (/me)"]
)
async def update_user_me(
    user_in: UserUpdate, # Schema containing optional name, avatar_uri
    current_user: User = Depends(get_current_active_user)
):
    """Updates limited profile fields (name, avatar) for the logged-in user."""
    logger.info(f"Attempting profile update for user: {current_user.email}")
    update_data = user_in.model_dump(exclude_unset=True)

    if not update_data:
         logger.warning(f"Update request for user '{current_user.email}' received no data.")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided.")

    updated_fields_count = 0
    # Explicitly define fields modifiable via this endpoint for security
    allowed_fields = ["name", "avatar_uri"]
    # Example: If users could update phone/age/gender themselves:
    # allowed_fields = ["name", "avatar_uri", "phone_number", "age", "gender"]

    for field, value in update_data.items():
        if field not in allowed_fields:
             logger.warning(f"User '{current_user.email}' attempted to update restricted field '{field}' via PATCH /me. Ignoring.")
             continue # Ignore disallowed fields silently

        if hasattr(current_user, field):
            # Only set if the value is different
            if getattr(current_user, field) != value:
                 setattr(current_user, field, value)
                 updated_fields_count += 1
                 # Avoid logging potentially sensitive URLs or long strings fully
                 display_value = "'URI updated'" if field == 'avatar_uri' and value else value
                 logger.debug(f"Staged update for user '{current_user.email}': {field} = {display_value}")
            else:
                 logger.debug(f"Skipping update for user '{current_user.email}': Field '{field}' unchanged.")
        else:
            # Should not happen if allowed_fields matches User model
            logger.warning(f"User '{current_user.email}' attempted to update non-existent field '{field}' (schema/model mismatch?).")

    # Save only if changes were actually staged
    if updated_fields_count > 0:
        try:
            await current_user.save() # Triggers before_save hook (updated_at)
            logger.info(f"Profile updated successfully ({updated_fields_count} fields) for user: {current_user.email}")
        except Exception as e:
            logger.exception(f"Database error saving profile update for user {current_user.email}:")
            raise HTTPException(status_code=500, detail="Could not save profile changes.")
    else:
         logger.info(f"No actual changes detected for user '{current_user.email}'. No save operation performed.")

    # Re-check ID after potential save, though save() shouldn't remove it
    if not current_user.id:
        logger.error(f"User object for '{current_user.email}' missing 'id' after potential save.")
        raise HTTPException(status_code=500, detail="Internal server error: User data incomplete after update.")

    # Return the updated user data
    user_read_data = {
        "id": str(current_user.id), "email": current_user.email, "name": current_user.name,
        "avatar_uri": str(current_user.avatar_uri) if current_user.avatar_uri else None,
        "is_active": current_user.is_active, "user_type": current_user.user_type,
        "created_at": current_user.created_at, "updated_at": current_user.updated_at
    }
    # Alternative: return UserRead.model_validate(current_user)
    return UserRead(**user_read_data)


# Schema UserPasswordUpdate needs to be defined (e.g., in app/schemas/user.py)
# with fields: current_password: str, new_password: str (with validation)
@router.put(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update Current User Password",
    description="Allows the authenticated user to change their own password after verifying the current one.",
    tags=["Users - Current User (/me)"],
    responses={
        204: {"description": "Password updated successfully"},
        400: {"description": "Incorrect current password or invalid new password format"},
        422: {"description": "Validation error in input data (e.g., missing fields)"}
    }
)
async def update_user_password(
    password_in: UserPasswordUpdate, # Assumed defined in schemas
    current_user: User = Depends(get_current_active_user)
):
    """Handles secure password change for the logged-in user."""
    logger.info(f"Password change attempt for user: {current_user.email}")

    # 1. Verify current password
    if not verify_password(password_in.current_password, current_user.hashed_password):
        logger.warning(f"Password change failed for user '{current_user.email}': Incorrect current password.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password."
        )

    # 2. Hash the new password (schema validation should enforce complexity/length)
    try:
        new_hashed_password = get_password_hash(password_in.new_password)
    except Exception as e:
        logger.exception(f"Password hashing failed during password update for user '{current_user.email}'.")
        raise HTTPException(status_code=500, detail="Error processing new password.")

    # 3. Update the user document
    try:
        current_user.hashed_password = new_hashed_password
        await current_user.save() # Triggers before_save for updated_at
        logger.info(f"Password updated successfully for user: {current_user.email}")

        # --- Optional: Invalidate older tokens here ---
        # If using a token blacklist (e.g., in Redis), add logic here:
        # try:
        #    await blacklist_tokens_for_user(current_user.id)
        #    logger.info(f"Successfully blacklisted old tokens for user {current_user.email}")
        # except Exception as blacklist_e:
        #    logger.error(f"Failed to blacklist tokens for user {current_user.email} after password change: {blacklist_e}")
        # ---------------------------------------------

        # Return No Content (FastAPI handles this when returning None)
        return None

    except Exception as e:
        logger.exception(f"Database error saving new password for user {current_user.email}:")
        raise HTTPException(status_code=500, detail="Could not update password.")


@router.post(
    "/me/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate Current User Account",
    description="Allows the authenticated user to deactivate their own account. This is reversible by an administrator.",
    tags=["Users - Current User (/me)"],
    responses={
        204: {"description": "Account deactivated successfully"},
    }
)
async def deactivate_user_me(
    current_user: User = Depends(get_current_active_user)
):
    """Sets the user's account status to inactive."""
    logger.warning(f"User '{current_user.email}' requested self-deactivation.")

    if not current_user.is_active or current_user.status != UserStatus.ACTIVE:
        logger.info(f"User '{current_user.email}' is already inactive or in a non-active state.")
        # Operation is idempotent; return success even if already inactive.
        return None

    try:
        current_user.is_active = False
        # Status is likely handled by model validator based on is_active, but setting explicitly is fine.
        current_user.status = UserStatus.INACTIVE
        await current_user.save()
        logger.info(f"User account '{current_user.email}' deactivated successfully.")

        # --- Optional: Invalidate all tokens for this user ---
        # If using a token blacklist:
        # try:
        #    await blacklist_tokens_for_user(current_user.id)
        #    logger.info(f"Successfully blacklisted tokens for deactivated user {current_user.email}")
        # except Exception as blacklist_e:
        #    logger.error(f"Failed to blacklist tokens for user {current_user.email} after deactivation: {blacklist_e}")
        # ----------------------------------------------------

        # Return No Content
        return None
    except Exception as e:
        logger.exception(f"Database error deactivating account for user {current_user.email}:")
        raise HTTPException(status_code=500, detail="Could not deactivate account.")