# app/api/v1/endpoints/admin.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import List, Optional, Any
from beanie.odm.operators.update.general import Set

from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings
from app.db.models.enums import UserStatus, UserType
from app.schemas.user import UserCreate, UserRead
from app.schemas.admin import AdminUserCreate, AdminUserUpdate 
from app.core.security import get_password_hash
from app.api.deps import get_current_admin_user

# Get logger instance
logger = logging.getLogger(__name__)

router = APIRouter()

# =========================================
# User Management Endpoints (Admin Only)
# =========================================

# --- POST /admin/users (create_any_user) ---
@router.post( "/users", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary="Create any type of User (Admin Only)", description="Allows an authenticated Admin user to create a new user with a specified role.", tags=["Admin - Users"] )
async def create_any_user( user_in: AdminUserCreate, current_admin: User = Depends(get_current_admin_user) ):
    logger.info(f"Admin {current_admin.email} attempting to create user: {user_in.email} with type: {user_in.user_type}")
    existing_user = await User.find_one(User.email == user_in.email)
    if existing_user:
        logger.warning(f"Failed to create user: Email '{user_in.email}' already exists.")
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail=f"An account with email '{user_in.email}' already exists.", )
    try: hashed_password = get_password_hash(user_in.password)
    except Exception as e: logger.error("Password hashing failed: %s", e, exc_info=True); raise HTTPException(status_code=500, detail="Error processing password.")
    new_user = User( email=user_in.email, name=user_in.name, hashed_password=hashed_password, user_type=user_in.user_type, status=UserStatus.ACTIVE, is_active=True, phone_number=user_in.phone_number, age=user_in.age, gender=user_in.gender, avatar_uri=user_in.avatar_uri )
    try:
        inserted_user = await new_user.insert()
        if not inserted_user or not inserted_user.id: logger.error("DB insert succeeded but user ID missing for email %s", user_in.email); raise HTTPException(status_code=500, detail="Failed to retrieve user details after creation.")
        logger.info(f"Admin {current_admin.email} created user {inserted_user.email} (ID: {inserted_user.id})")
        # --- Optionally create default settings upon user creation ---
        try:
            default_parental = ParentalSettings(user=inserted_user) # type: ignore Link assignment
            await default_parental.insert()
            logger.info(f"Created default ParentalSettings for user {inserted_user.id}")
            default_appearance = AppearanceSettings(user=inserted_user) # type: ignore Link assignment
            await default_appearance.insert()
            logger.info(f"Created default AppearanceSettings for user {inserted_user.id}")
        except Exception as settings_e:
             logger.error("Failed to create default settings for user %s: %s", inserted_user.id, settings_e, exc_info=True)
             # Decide if user creation should fail if default settings fail - likely yes
             # await inserted_user.delete() # Rollback user creation
             # raise HTTPException(status_code=500, detail="Failed to initialize user settings.")
             # Or just log the error and continue
        # ---------------------------------------------------------
    except Exception as e: logger.error("DB error during user creation for email %s: %s", user_in.email, e, exc_info=True); raise HTTPException(status_code=500, detail="Database error creating user.")
    user_read_data = { "id": str(inserted_user.id), "email": inserted_user.email, "name": inserted_user.name, "avatar_uri": inserted_user.avatar_uri, "is_active": inserted_user.is_active, "user_type": inserted_user.user_type, "created_at": inserted_user.created_at, "updated_at": inserted_user.updated_at }
    return UserRead(**user_read_data)

# --- GET /admin/users (list_users) ---
@router.get( "/users", response_model=List[UserRead], summary="List Users (Admin Only)", description="Retrieves a list of users with optional filtering and pagination.", tags=["Admin - Users"] )
async def list_users( skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), user_type: Optional[UserType] = Query(None), status: Optional[UserStatus] = Query(None), current_admin: User = Depends(get_current_admin_user) ):
    logger.info(f"Admin {current_admin.email} requested user list: skip={skip}, limit={limit}, type={user_type}, status={status}")
    query_filter = {}
    if user_type: query_filter["user_type"] = user_type
    if status: query_filter["status"] = status
    try:
        users_cursor = User.find(query_filter).skip(skip).limit(limit)
        users_list = await users_cursor.to_list()
        response_data = []
        for user in users_list:
             if user.id:
                user_read_data = { "id": str(user.id), "email": user.email, "name": user.name, "avatar_uri": user.avatar_uri, "is_active": user.is_active, "user_type": user.user_type, "created_at": user.created_at, "updated_at": user.updated_at }
                response_data.append(UserRead(**user_read_data))
        return response_data
    except Exception as e: logger.error("Error fetching user list: %s", e, exc_info=True); raise HTTPException(status_code=500, detail="Could not retrieve user list.")

# --- GET /admin/users/{user_id} (get_user_by_id) ---
@router.get( "/users/{user_id}", response_model=UserRead, summary="Get User by ID (Admin Only)", description="Retrieves details for a specific user by their ID.", tags=["Admin - Users"], responses={404: {"description": "User not found"}} )
async def get_user_by_id( user_id: str, current_admin: User = Depends(get_current_admin_user) ):
    logger.info(f"Admin {current_admin.email} requesting details for user ID: {user_id}")
    try:
        user = await User.get(user_id)
        if not user: logger.warning(f"User ID '{user_id}' not found (Admin: {current_admin.email})"); raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not user.id: logger.error(f"User fetched for ID {user_id} but has no .id attribute"); raise HTTPException(status_code=500, detail="Error retrieving user details")
        user_read_data = { "id": str(user.id), "email": user.email, "name": user.name, "avatar_uri": user.avatar_uri, "is_active": user.is_active, "user_type": user.user_type, "created_at": user.created_at, "updated_at": user.updated_at }
        return UserRead(**user_read_data)
    except HTTPException: raise # Re-raise HTTPException (like 404) directly
    except Exception as e: logger.error("Error fetching user ID %s: %s", user_id, e, exc_info=True); raise HTTPException(status_code=500, detail="Could not retrieve user details.")

# --- PATCH /admin/users/{user_id} (update_user_by_admin) ---
@router.patch( "/users/{user_id}", response_model=UserRead, summary="Update User by ID (Admin Only)", description="Allows an Admin to update certain fields of any user.", tags=["Admin - Users"], responses={404: {"description": "User not found"}} )
async def update_user_by_admin( user_id: str, user_in: AdminUserUpdate, current_admin: User = Depends(get_current_admin_user) ):
    logger.info(f"Admin {current_admin.email} attempting update for user ID: {user_id} with data: {user_in.model_dump(exclude_unset=True)}")
    user_to_update = await User.get(user_id)
    if not user_to_update: logger.warning(f"Update failed: User ID '{user_id}' not found."); raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    update_data = user_in.model_dump(exclude_unset=True)
    if not update_data: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    # If 'is_active' is being changed, update 'status' accordingly (handled by model validator now)
    # update_query = Set(update_data) # model validator handles status update now
    try:
        # Update fields directly (model validator handles status consistency)
        for field, value in update_data.items():
             if hasattr(user_to_update, field):
                 setattr(user_to_update, field, value)
             else:
                  logger.warning(f"Attempted to update non-existent field '{field}' on user {user_id}")

        await user_to_update.save() # Use save() to trigger before_save hook and validators
        updated_user = user_to_update # Use the instance after save

        # --- Replaced Beanie update with direct save() to trigger hooks ---
        # result = await user_to_update.update(update_query)
        # if result is None: raise HTTPException(status_code=500, detail="Failed to update user.")
        # updated_user = await User.get(user_id) # Fetch again needed with Beanie update()
        # -----------------------------------------------------------------

        if not updated_user or not updated_user.id: logger.error(f"Failed to fetch/confirm user ID '{user_id}' after update."); raise HTTPException(status_code=500, detail="Failed to fetch updated user data.")
        logger.info(f"Admin {current_admin.email} successfully updated user ID: {user_id}")
        user_read_data = { "id": str(updated_user.id), "email": updated_user.email, "name": updated_user.name, "avatar_uri": updated_user.avatar_uri, "is_active": updated_user.is_active, "user_type": updated_user.user_type, "created_at": updated_user.created_at, "updated_at": updated_user.updated_at }
        return UserRead(**user_read_data)
    except Exception as e: logger.error("Error updating user ID %s: %s", user_id, e, exc_info=True); raise HTTPException(status_code=500, detail="Could not update user.")

# --- DELETE /admin/users/{user_id} (delete_user) ---
@router.delete( "/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete User by ID (Admin Only)", description="Permanently deletes a user account and associated settings.", tags=["Admin - Users"], responses={ 404: {"description": "User not found"}, 403: {"description": "Admin cannot delete themselves"}, } )
async def delete_user( user_id: str, current_admin: User = Depends(get_current_admin_user) ):
    logger.warning(f"Admin {current_admin.email} attempting to DELETE user ID: {user_id}")
    if str(current_admin.id) == user_id: logger.error(f"Admin {current_admin.email} attempted self-deletion."); raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrators cannot delete their own account.")

    user_to_delete = await User.get(user_id)
    if not user_to_delete: logger.warning(f"Deletion failed: User ID '{user_id}' not found."); raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        # --- Delete related settings documents FIRST ---
        deleted_parental_count = await ParentalSettings.find(ParentalSettings.user.id == user_to_delete.id).delete() # type: ignore
        logger.info(f"Deleted {deleted_parental_count.deleted_count} ParentalSettings document(s) for user {user_id}")

        deleted_appearance_count = await AppearanceSettings.find(AppearanceSettings.user.id == user_to_delete.id).delete() # type: ignore
        logger.info(f"Deleted {deleted_appearance_count.deleted_count} AppearanceSettings document(s) for user {user_id}")
        # --------------------------------------------

        # --- Now delete the user ---
        delete_result = await user_to_delete.delete()
        # ---------------------------

        if delete_result and delete_result.deleted_count > 0:
            logger.info(f"Admin {current_admin.email} successfully deleted user ID: {user_id}")
            return None # Return None for 204 No Content
        else:
             logger.error(f"User document deletion failed for ID: {user_id}, although related data might be deleted.")
             # This indicates an issue if settings were deleted but user wasn't
             raise HTTPException(status_code=500, detail="User deletion failed after attempting cleanup.")

    except Exception as e:
        logger.error("Error during deletion process for user ID %s: %s", user_id, e, exc_info=True)
        # Consider rollback mechanisms in a real production scenario if partial deletion occurs
        raise HTTPException(status_code=500, detail="Could not complete user deletion process.")