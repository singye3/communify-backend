# app/api/v1/endpoints/admin.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query # Removed Body as it wasn't directly used
from typing import List, Optional, Any
# Beanie imports removed as direct operators like Set weren't used here.
# from beanie.odm.operators.update.general import Set
from beanie.exceptions import RevisionIdWasChanged
from pydantic import ValidationError # Keep for catching Pydantic errors during update

# --- App Imports ---
from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings
from app.db.models.enums import UserStatus, UserType # Assuming enums are here
from app.schemas.user import UserRead
from app.schemas.admin import AdminUserCreate, AdminUserUpdate
from app.core.security import get_password_hash
from app.api.deps import get_current_admin_user

# --- Get Logger ---
logger = logging.getLogger(__name__)

# --- API Router ---
router = APIRouter()

# =========================================
# User Management Endpoints (Admin Only)
# =========================================

@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create User (Admin Only)",
    description="Allows an authenticated Admin user to create a new user with any specified role (Parent, Child, Admin). Initializes default settings for the new user.",
    tags=["Admin - Users"]
)
async def create_any_user(
    user_in: AdminUserCreate,
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Creates a new user with a specified user type. Requires ADMIN privileges.
    Handles email uniqueness check, password hashing, and initialization of default settings.
    """
    logger.info(f"Admin '{current_admin.email}' attempting to create user: '{user_in.email}' with type: '{user_in.user_type}'")

    # --- Check for existing user ---
    existing_user = await User.find_one(User.email == user_in.email)
    if existing_user:
        logger.warning(f"Failed to create user: Email '{user_in.email}' already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{user_in.email}' already exists.",
        )

    # --- Hash password ---
    try:
        hashed_password = get_password_hash(user_in.password)
    except Exception as e:
        # Use logger.exception to include traceback automatically
        logger.exception("Password hashing failed during user creation for email %s.", user_in.email)
        raise HTTPException(status_code=500, detail="Error processing user data.")

    # --- Create User Document ---
    # Ensure all fields from AdminUserCreate are mapped correctly to User model
    new_user_data = user_in.model_dump()
    new_user = User(
        **new_user_data, # Pass validated data
        hashed_password=hashed_password,
        status=UserStatus.ACTIVE, # Overwrite default status if needed, or use schema's
        is_active=user_in.is_active if user_in.is_active is not None else True # Use schema default or True
        # Remove 'password' from the data passed to User model if it's still there
        # Beanie/Pydantic might ignore extra fields, but good practice to exclude
    )
    # Or explicitly map:
    # new_user = User(
    #     email=user_in.email, name=user_in.name, hashed_password=hashed_password,
    #     user_type=user_in.user_type, status=user_in.status or UserStatus.ACTIVE,
    #     is_active=user_in.is_active if user_in.is_active is not None else True,
    #     phone_number=user_in.phone_number, age=user_in.age, gender=user_in.gender,
    #     avatar_uri=user_in.avatar_uri
    # )


    # --- Insert User and Default Settings ---
    inserted_user: Optional[User] = None
    try:
        inserted_user = await new_user.insert()
        if not inserted_user or not inserted_user.id:
             logger.critical("CRITICAL: Database insert reported success but user object/ID is missing for email %s", user_in.email)
             raise HTTPException(status_code=500, detail="Failed to confirm user creation after insert.")

        logger.info(f"Admin '{current_admin.email}' created user '{inserted_user.email}' (ID: {inserted_user.id})")

        # --- Create default settings ---
        # NOTE: This part is not atomic with user creation. Consider transactions for strict consistency.
        try:
            # Use Link reference correctly
            default_parental = ParentalSettings(user=inserted_user) # type: ignore
            await default_parental.insert()
            logger.info(f"Created default ParentalSettings for user {inserted_user.id}")
        except Exception as e_parental:
            logger.error("Failed to create default ParentalSettings for user %s: %s", inserted_user.id, e_parental, exc_info=True)
            # Trigger rollback: Attempt to delete the created user
            await inserted_user.delete()
            logger.warning(f"Rolled back creation of user {inserted_user.id} due to ParentalSettings failure.")
            raise HTTPException(status_code=500, detail="Failed to initialize user settings (Parental). User creation rolled back.")

        try:
            default_appearance = AppearanceSettings(user=inserted_user) # type: ignore
            await default_appearance.insert()
            logger.info(f"Created default AppearanceSettings for user {inserted_user.id}")
        except Exception as e_appearance:
             logger.error("Failed to create default AppearanceSettings for user %s: %s", inserted_user.id, e_appearance, exc_info=True)
             # Rollback user and parental settings
             await ParentalSettings.find_one(ParentalSettings.user.id == inserted_user.id).delete() # type: ignore
             await inserted_user.delete()
             logger.warning(f"Rolled back creation of user {inserted_user.id} and ParentalSettings due to AppearanceSettings failure.")
             raise HTTPException(status_code=500, detail="Failed to initialize user settings (Appearance). User creation rolled back.")

    except Exception as e_user:
        # Catch potential database errors during user insert itself
        logger.exception("Database error during user insertion for email %s.", user_in.email)
        # Cleanup if user object exists (might be redundant if insert failed cleanly)
        if inserted_user and hasattr(inserted_user, 'delete'):
             logger.warning("Attempting cleanup for potentially partially inserted user %s", inserted_user.id or user_in.email)
             await inserted_user.delete() # Requires inserted_user to be a valid Beanie doc
        raise HTTPException(status_code=500, detail="Database error during user registration.")

    # --- Prepare and Return Response ---
    # Ensure all fields required by UserRead are present
    user_read_data = {
        "id": str(inserted_user.id), "email": inserted_user.email, "name": inserted_user.name,
        "avatar_uri": str(inserted_user.avatar_uri) if inserted_user.avatar_uri else None, # Ensure HttpUrl is stringified if needed
        "is_active": inserted_user.is_active, "user_type": inserted_user.user_type,
        "created_at": inserted_user.created_at, "updated_at": inserted_user.updated_at
    }
    # Alternative: return UserRead.model_validate(inserted_user)
    return UserRead(**user_read_data)


# --- GET /admin/users (list_users) ---
@router.get(
    "/users",
    response_model=List[UserRead],
    summary="List Users (Admin Only)",
    description="Retrieves a list of users with optional filtering and pagination.",
    tags=["Admin - Users"]
)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip (offset)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records per page"),
    user_type: Optional[UserType] = Query(None, description="Filter by user type"),
    status: Optional[UserStatus] = Query(None, description="Filter by user status"),
    email_search: Optional[str] = Query(None, description="Search by partial email match (case-insensitive)"),
    name_search: Optional[str] = Query(None, description="Search by partial name match (case-insensitive)"),
    current_admin: User = Depends(get_current_admin_user)
):
    """Lists users with pagination and filtering options. Requires ADMIN privileges."""
    logger.info(f"Admin '{current_admin.email}' requested user list: skip={skip}, limit={limit}, type={user_type}, status={status}, email='{email_search}', name='{name_search}'")

    query_filter = {}
    if user_type: query_filter[User.user_type] = user_type # Use model field for clarity
    if status: query_filter[User.status] = status
    if email_search: query_filter[User.email] = {"$regex": email_search, "$options": "i"}
    if name_search: query_filter[User.name] = {"$regex": name_search, "$options": "i"}

    try:
        users_cursor = User.find(query_filter).sort(-User.created_at).skip(skip).limit(limit)
        users_list = await users_cursor.to_list()

        response_data = []
        for user in users_list:
             if user.id:
                # Ensure correct field mapping for UserRead
                user_read_data = {
                    "id": str(user.id), "email": user.email, "name": user.name,
                    "avatar_uri": str(user.avatar_uri) if user.avatar_uri else None,
                    "is_active": user.is_active, "user_type": user.user_type,
                    "created_at": user.created_at, "updated_at": user.updated_at
                }
                response_data.append(UserRead(**user_read_data))
                # Alternative: response_data.append(UserRead.model_validate(user))
             else:
                 # Log users found in query that somehow lack an ID
                 logger.error(f"User found in list query (filter: {query_filter}) but missing ID: email='{getattr(user, 'email', 'N/A')}'")

        logger.debug(f"Returning {len(response_data)} users for admin list request by '{current_admin.email}'.")
        return response_data
    except Exception as e:
        logger.exception(f"Error fetching user list for admin '{current_admin.email}':")
        raise HTTPException(status_code=500, detail="Could not retrieve user list.")


# --- GET /admin/users/{user_id} (get_user_by_id) ---
@router.get(
    "/users/{user_id}",
    response_model=UserRead,
    summary="Get User by ID (Admin Only)",
    description="Retrieves details for a specific user by their ID.",
    tags=["Admin - Users"],
    responses={404: {"description": "User not found"}}
)
async def get_user_by_id(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user)
):
    """Retrieves a specific user by ID. Requires ADMIN privileges."""
    logger.info(f"Admin '{current_admin.email}' requesting details for user ID: {user_id}")
    try:
        # User.get() performs lookup by primary key (_id)
        user = await User.get(user_id)

        if not user:
            logger.warning(f"User ID '{user_id}' not found (Admin request: '{current_admin.email}')")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Belt-and-suspenders check, User.get should ensure ID is present if doc is found
        if not user.id:
            logger.error(f"User fetched for ID {user_id} but has no .id attribute (data inconsistency?)")
            raise HTTPException(status_code=500, detail="Error retrieving user details - inconsistent data.")

        # Prepare response data manually or use model_validate
        user_read_data = {
             "id": str(user.id), "email": user.email, "name": user.name,
             "avatar_uri": str(user.avatar_uri) if user.avatar_uri else None,
             "is_active": user.is_active, "user_type": user.user_type,
             "created_at": user.created_at, "updated_at": user.updated_at
        }
        logger.debug(f"Successfully retrieved user details for ID: {user_id} for admin '{current_admin.email}'")
        # Alternative: return UserRead.model_validate(user)
        return UserRead(**user_read_data)

    except HTTPException:
        raise # Re-raise specific HTTP exceptions (like 404)
    except Exception as e:
        logger.exception(f"Error fetching user by ID {user_id} for admin '{current_admin.email}':")
        raise HTTPException(status_code=500, detail="Could not retrieve user details.")


# --- PATCH /admin/users/{user_id} (update_user_by_admin) ---
@router.patch(
    "/users/{user_id}",
    response_model=UserRead,
    summary="Update User by ID (Admin Only)",
    description="Allows an Admin to update certain user fields like name, status, type, active status etc.",
    tags=["Admin - Users"],
    responses={
        404: {"description": "User not found"},
        400: {"description": "No update data provided"},
        409: {"description": "Conflict due to concurrent update"},
        422: {"description": "Validation error in provided data"}
    }
)
async def update_user_by_admin(
    user_id: str,
    user_in: AdminUserUpdate, # Specific schema for admin updates
    current_admin: User = Depends(get_current_admin_user)
):
    """Updates user information based on fields provided in the request body."""
    logger.info(f"Admin '{current_admin.email}' attempting update for user ID: {user_id}")

    user_to_update = await User.get(user_id)
    if not user_to_update:
        logger.warning(f"Update failed: User ID '{user_id}' not found (Admin: '{current_admin.email}').")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get only the fields that were actually sent in the request body
    update_data = user_in.model_dump(exclude_unset=True)
    if not update_data:
        logger.warning(f"Update request for user {user_id} by admin '{current_admin.email}' had no data to update.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    logger.debug(f"Applying update data to user {user_id}: {update_data}")

    try:
        updated_fields_count = 0
        # Update fields directly on the fetched Beanie document
        for field, value in update_data.items():
            if hasattr(user_to_update, field):
                # Only update if the value has actually changed
                if getattr(user_to_update, field) != value:
                    setattr(user_to_update, field, value)
                    updated_fields_count += 1
                    logger.debug(f"User {user_id} field '{field}' set to '{value}'")
                else:
                    logger.debug(f"Skipping update for user {user_id}: Field '{field}' value unchanged ('{value}').")
            else:
                # Log attempts to update fields not present on the model (might indicate schema mismatch)
                logger.warning(f"Attempted to update non-existent field '{field}' on User model for ID {user_id}")

        # Save only if changes were actually applied to trigger hooks/validation
        if updated_fields_count > 0:
            # user_to_update.save() triggers before_save hook and model validators
            # It raises RevisionIdWasChanged on conflict
            await user_to_update.save()
            logger.info(f"Admin '{current_admin.email}' successfully updated {updated_fields_count} field(s) for user ID: {user_id}")
            updated_user = user_to_update # Use the instance potentially modified by save()
        else:
            logger.info(f"No effective changes applied for user {user_id} by admin '{current_admin.email}'. Save skipped.")
            updated_user = user_to_update # Return the existing user data unchanged

        if not updated_user or not updated_user.id:
            logger.error(f"User object invalid after update attempt for ID '{user_id}'.")
            raise HTTPException(status_code=500, detail="Failed to process user data after update.")

        # Prepare response data
        user_read_data = {
             "id": str(updated_user.id), "email": updated_user.email, "name": updated_user.name,
             "avatar_uri": str(updated_user.avatar_uri) if updated_user.avatar_uri else None,
             "is_active": updated_user.is_active, "user_type": updated_user.user_type,
             "created_at": updated_user.created_at, "updated_at": updated_user.updated_at
        }
        # Alternative: return UserRead.model_validate(updated_user)
        return UserRead(**user_read_data)

    except ValidationError as e: # Catch Pydantic errors during setattr or save validation
         logger.warning(f"Validation error during user update for ID {user_id} by admin '{current_admin.email}': {e.errors()}", exc_info=False) # Don't need full trace usually
         raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except RevisionIdWasChanged: # Catch Beanie specific error for concurrent updates
         logger.warning(f"Concurrency error: User {user_id} was modified during update attempt by admin '{current_admin.email}'.")
         raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User data was modified concurrently. Please refresh and retry.")
    except Exception as e:
        logger.exception(f"Error updating user ID {user_id} by admin '{current_admin.email}':")
        raise HTTPException(status_code=500, detail="Could not update user.")


# --- DELETE /admin/users/{user_id} (delete_user) ---
@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User by ID (Admin Only)",
    description="Permanently deletes a user account and associated settings documents. Admins cannot delete themselves.",
    tags=["Admin - Users"],
    responses={
        204: {"description": "User successfully deleted"},
        404: {"description": "User not found"},
        403: {"description": "Admin cannot delete themselves"},
    }
)
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user)
):
    """Deletes a user and their associated settings. Requires ADMIN privileges."""
    logger.warning(f"Admin '{current_admin.email}' attempting to DELETE user ID: {user_id}")

    # Prevent self-deletion
    if str(current_admin.id) == user_id:
        logger.error(f"Admin '{current_admin.email}' (ID: {current_admin.id}) attempted self-deletion.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrators cannot delete their own account.")

    # Find user first to ensure they exist and get their ObjectId
    user_to_delete = await User.get(user_id)
    if not user_to_delete:
        logger.warning(f"Deletion failed: User ID '{user_id}' not found (Admin: '{current_admin.email}').")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user_to_delete.id:
         logger.error(f"Found user for deletion (ID: {user_id}) but instance is missing '.id'. Aborting deletion.")
         raise HTTPException(status_code=500, detail="Internal error retrieving user ID for deletion.")

    # --- Perform Deletion (Manual Cascade) ---
    # NOTE: This is not atomic. Consider transactions for strict consistency.
    try:
        user_obj_id = user_to_delete.id # Use the actual ObjectId

        # 1. Delete related settings first
        # Use Beanie's find with a filter on the linked user's ID
        # The filter syntax for Links uses the linked document's primary key field ('_id')
        deleted_parental_result = await ParentalSettings.find(ParentalSettings.user.id == user_obj_id).delete() # type: ignore
        deleted_parental_count = deleted_parental_result.deleted_count if deleted_parental_result else 0
        logger.info(f"Deleted {deleted_parental_count} ParentalSettings document(s) for user {user_id}")

        deleted_appearance_result = await AppearanceSettings.find(AppearanceSettings.user.id == user_obj_id).delete() # type: ignore
        deleted_appearance_count = deleted_appearance_result.deleted_count if deleted_appearance_result else 0
        logger.info(f"Deleted {deleted_appearance_count} AppearanceSettings document(s) for user {user_id}")

        # 2. Now delete the user document itself
        delete_result = await user_to_delete.delete()

        if delete_result and delete_result.deleted_count > 0:
            logger.info(f"Admin '{current_admin.email}' successfully DELETED user ID: {user_id} and associated settings.")
            # Return None for 204 No Content response
            return None
        else:
             # This might happen if the user was deleted between the .get() and .delete() calls (race condition)
             # or if the delete operation failed for some reason.
             logger.error(f"User document deletion failed or reported 0 deleted for ID: {user_id}. Result: {delete_result}")
             # Find the user again to check if they still exist
             check_user = await User.get(user_id)
             if check_user:
                  raise HTTPException(status_code=500, detail="User deletion failed unexpectedly.")
             else:
                  # User seems to be gone now, maybe concurrent deletion? Log and treat as success (idempotency).
                  logger.warning(f"User {user_id} not found after delete operation reported 0 count. Assuming already deleted.")
                  return None # Return 204 anyway

    except Exception as e:
        logger.exception(f"Error during deletion process for user ID {user_id} initiated by admin '{current_admin.email}':")
        # Consider more specific error handling if needed
        raise HTTPException(status_code=500, detail="Could not complete the user deletion process.")