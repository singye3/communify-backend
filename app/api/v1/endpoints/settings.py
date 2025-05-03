# app/api/v1/endpoints/settings.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from pydantic import ValidationError

# --- App Imports ---
from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings
from app.schemas.settings import ParentalSettingsRead, ParentalSettingsUpdate, ParentalSettingsBase
from app.schemas.appearance import AppearanceSettingsRead, AppearanceSettingsUpdate, AppearanceSettingsBase
from app.api.deps import get_current_active_user

# --- Get Logger ---
logger = logging.getLogger(__name__)

# --- API Router ---
router = APIRouter()

# ============================
# PARENTAL SETTINGS ENDPOINTS
# ============================

@router.get(
    "/parental",
    response_model=ParentalSettingsRead,
    summary="Get Parental Settings",
    description="Retrieves the parental control settings for the currently authenticated user. Returns default settings if none have been saved previously.",
    tags=["Settings - Parental"]
)
async def read_parental_settings(
    current_user: User = Depends(get_current_active_user)
):
    """
    Fetches the parental settings document linked to the logged-in user.
    If no document exists, it constructs and returns a default settings object.
    """
    logger.debug(f"Fetching parental settings for user: {current_user.email}")
    try:
        settings = await ParentalSettings.find_one(ParentalSettings.user.id == current_user.id) # type: ignore

        if not settings:
            logger.info(f"No parental settings found for user {current_user.email}. Returning defaults.")
            # Create a default response using the Base schema's defaults
            default_data = ParentalSettingsBase().model_dump(by_alias=True) # Use by_alias if needed
            # Use a specific ID or None to indicate defaults were returned
            return ParentalSettingsRead(id="defaults_returned", **default_data)

        if not settings.id:
             logger.error(f"ParentalSettings document found for user {current_user.email} but missing _id.")
             raise HTTPException(status_code=500, detail="Error retrieving settings ID.")

        settings_data = settings.model_dump(by_alias=True) # Use by_alias if needed

        # --- FIX APPLIED HERE ---
        # Ensure the '_id' key (the alias for 'id') holds the string representation
        if '_id' in settings_data and settings.id:
             settings_data['_id'] = str(settings.id)
        elif settings.id: # Fallback just in case model_dump didn't include it but id exists
             settings_data['_id'] = str(settings.id)
        # ------------------------

        logger.debug(f"Parental settings retrieved successfully for user: {current_user.email}")
        # Pydantic will now correctly use the string value associated with '_id' to populate the 'id' field.
        return ParentalSettingsRead(**settings_data)

    except Exception as e:
        # Catch potential Pydantic validation error during ParentalSettingsRead instantiation
        if isinstance(e, ValidationError):
             logger.warning(f"Validation error creating ParentalSettingsRead response for user {current_user.email}: {e.errors()}")
             # Depending on policy, you might still want to return 500 or a modified response
             raise HTTPException(status_code=500, detail="Error processing retrieved settings.")
        logger.exception(f"Error fetching parental settings for user {current_user.email}:")
        raise HTTPException(status_code=500, detail="Could not retrieve parental settings.")


# Changed from PUT to PATCH for semantic accuracy (partial update)
@router.patch(
    "/parental",
    response_model=ParentalSettingsRead,
    summary="Update Parental Settings",
    description="Creates or partially updates the parental control settings for the currently authenticated user. Only provided fields are modified.",
    tags=["Settings - Parental"]
)
async def update_parental_settings(
    settings_in: ParentalSettingsUpdate, # Schema defining updatable fields (all optional)
    current_user: User = Depends(get_current_active_user)
):
    """
    Updates (or creates if non-existent) the parental settings document
    for the logged-in user using a PATCH method. Only applies changes
    for fields present in the request body.
    """
    logger.info(f"Updating parental settings for user: {current_user.email}")
    try:
        existing_settings = await ParentalSettings.find_one(ParentalSettings.user.id == current_user.id) # type: ignore

        # Get update data, excluding fields not sent by the client
        update_data = settings_in.model_dump(exclude_unset=True, by_alias=True) # Use by_alias if input might use aliases
        logger.debug(f"Update data received: {update_data}")

        if not update_data:
            logger.warning(f"No valid update data provided for parental settings by user {current_user.email}. Returning current state.")
            # Return current settings if they exist, otherwise return defaults
            if existing_settings:
                 settings_data = existing_settings.model_dump(by_alias=True)
                 # --- FIX APPLIED HERE (within no-update path) ---
                 if '_id' in settings_data and existing_settings.id:
                     settings_data['_id'] = str(existing_settings.id)
                 elif existing_settings.id:
                      settings_data['_id'] = str(existing_settings.id)
                 # -----------------------------------------------
                 if not existing_settings.id:
                      # Handle case where existing settings somehow lack ID, return default-like structure
                      logger.error(f"Existing parental settings for user {current_user.email} lack ID. Returning defaults.")
                      default_resp_data = ParentalSettingsBase().model_dump(by_alias=True)
                      return ParentalSettingsRead(id="error_missing_id", **default_resp_data)
                 return ParentalSettingsRead(**settings_data)

            else:
                default_data = ParentalSettingsBase().model_dump(by_alias=True)
                return ParentalSettingsRead(id="defaults_returned", **default_data)

        settings_to_return = None
        if existing_settings:
            logger.debug(f"Found existing parental settings for user {current_user.email}. Updating...")
            # Apply updates using Beanie's update method with $set
            await existing_settings.update({"$set": update_data})
            # Re-fetch the updated document to get latest state (e.g., updated_at)
            settings_to_return = await ParentalSettings.get(existing_settings.id) # type: ignore
            if not settings_to_return:
                 logger.error(f"Failed to fetch parental settings for user {current_user.email} immediately after update.")
                 raise HTTPException(status_code=500, detail="Failed to confirm settings update.")
            logger.info(f"Parental settings updated successfully for user: {current_user.email}")

        else:
            logger.info(f"No existing parental settings found for user {current_user.email}. Creating new document...")
            # Create new settings: merge incoming data with base defaults for a complete object
            # Important: Create a BASE model first to ensure defaults are applied before overlaying update_data
            base_defaults = ParentalSettingsBase().model_dump(by_alias=True)
            # Merge update_data onto base_defaults. update_data takes precedence.
            new_settings_data = {**base_defaults, **update_data}
            # Note: If Beanie/Pydantic handles default merging automatically on create, this explicit merge might be simplified.
            # Check Beanie's behavior for creating documents from partial data.
            new_settings = ParentalSettings(user=current_user, **new_settings_data) # type: ignore
            # insert() will run validators/hooks
            await new_settings.insert()
            settings_to_return = new_settings
            logger.info(f"Parental settings created successfully for user: {current_user.email}")

        if not settings_to_return or not settings_to_return.id:
            logger.error(f"Parental settings ID missing after save/insert for user {current_user.email}")
            raise HTTPException(status_code=500, detail="Failed to retrieve settings ID after update.")

        # Prepare and return response data
        response_data = settings_to_return.model_dump(by_alias=True)
        # --- FIX APPLIED HERE ---
        # Ensure the '_id' key holds the string representation
        if '_id' in response_data and settings_to_return.id:
             response_data['_id'] = str(settings_to_return.id)
        elif settings_to_return.id: # Fallback
              response_data['_id'] = str(settings_to_return.id)
        # ------------------------
        return ParentalSettingsRead(**response_data)

    except ValidationError as e: # Catch Pydantic validation errors during init or save
        logger.warning(f"Validation error updating parental settings for user {current_user.email}: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except Exception as e:
        logger.exception(f"Error updating parental settings for user {current_user.email}:")
        raise HTTPException(status_code=500, detail="Could not update parental settings.")


# ============================
# APPEARANCE SETTINGS ENDPOINTS
# ============================

@router.get(
    "/appearance",
    response_model=AppearanceSettingsRead,
    summary="Get Appearance Settings",
    description="Retrieves the appearance and interaction preferences for the currently authenticated user. Returns defaults if none saved.",
    tags=["Settings - Appearance"]
)
async def read_appearance_settings(
    current_user: User = Depends(get_current_active_user)
):
    """
    Fetches the appearance settings document linked to the logged-in user.
    Returns default settings if no specific settings document exists.
    """
    logger.debug(f"Fetching appearance settings for user: {current_user.email}")
    try:
        settings = await AppearanceSettings.find_one(AppearanceSettings.user.id == current_user.id) # type: ignore

        if not settings:
            logger.info(f"No appearance settings found for user {current_user.email}. Returning defaults.")
            default_data = AppearanceSettingsBase().model_dump(by_alias=True) # Use by_alias for consistency ('theme')
            return AppearanceSettingsRead(id="defaults_returned", **default_data)

        if not settings.id:
             logger.error(f"AppearanceSettings document found for user {current_user.email} but missing _id.")
             raise HTTPException(status_code=500, detail="Error retrieving settings ID.")

        settings_data = settings.model_dump(by_alias=True) # Use by_alias for consistency ('theme')

        # --- FIX APPLIED HERE ---
        # Ensure the '_id' key holds the string representation
        if '_id' in settings_data and settings.id:
             settings_data['_id'] = str(settings.id)
        elif settings.id: # Fallback
             settings_data['_id'] = str(settings.id)
        # ------------------------

        logger.debug(f"Appearance settings retrieved successfully for user: {current_user.email}")
        return AppearanceSettingsRead(**settings_data)

    except Exception as e:
         # Catch potential Pydantic validation error during AppearanceSettingsRead instantiation
        if isinstance(e, ValidationError):
             logger.warning(f"Validation error creating AppearanceSettingsRead response for user {current_user.email}: {e.errors()}")
             raise HTTPException(status_code=500, detail="Error processing retrieved settings.")
        logger.exception(f"Error fetching appearance settings for user {current_user.email}:")
        raise HTTPException(status_code=500, detail="Could not retrieve appearance settings.")


# Changed from PUT to PATCH for semantic accuracy (partial update)
@router.patch(
    "/appearance",
    response_model=AppearanceSettingsRead,
    summary="Update Appearance Settings",
    description="Creates or partially updates the appearance and interaction settings for the currently authenticated user. Only provided fields are modified.",
    tags=["Settings - Appearance"]
)
async def update_appearance_settings(
    settings_in: AppearanceSettingsUpdate, # Use Update schema (all fields optional)
    current_user: User = Depends(get_current_active_user)
):
    """
    Updates (or creates if non-existent) the appearance settings document
    for the logged-in user using a PATCH method. Applies partial changes.
    """
    logger.info(f"Updating appearance settings for user: {current_user.email}")
    try:
        existing_settings = await AppearanceSettings.find_one(AppearanceSettings.user.id == current_user.id) # type: ignore

        # Use by_alias=True if input might use 'theme' alias
        update_data = settings_in.model_dump(exclude_unset=True, by_alias=True)
        logger.debug(f"Update data received: {update_data}")

        if not update_data:
            logger.warning(f"No valid update data provided for appearance settings by user {current_user.email}. Returning current state.")
            if existing_settings:
                 settings_data = existing_settings.model_dump(by_alias=True)
                 # --- FIX APPLIED HERE (within no-update path) ---
                 if '_id' in settings_data and existing_settings.id:
                     settings_data['_id'] = str(existing_settings.id)
                 elif existing_settings.id:
                      settings_data['_id'] = str(existing_settings.id)
                 # -----------------------------------------------
                 if not existing_settings.id:
                      logger.error(f"Existing appearance settings for user {current_user.email} lack ID. Returning defaults.")
                      default_resp_data = AppearanceSettingsBase().model_dump(by_alias=True)
                      return AppearanceSettingsRead(id="error_missing_id", **default_resp_data)
                 return AppearanceSettingsRead(**settings_data)
            else:
                default_data = AppearanceSettingsBase().model_dump(by_alias=True)
                return AppearanceSettingsRead(id="defaults_returned", **default_data)

        settings_to_return = None
        if existing_settings:
            logger.debug(f"Found existing appearance settings for user {current_user.email}. Updating...")
            await existing_settings.update({"$set": update_data})
            settings_to_return = await AppearanceSettings.get(existing_settings.id) # type: ignore # Fetch updated doc
            if not settings_to_return:
                 logger.error(f"Failed to fetch appearance settings for user {current_user.email} immediately after update.")
                 raise HTTPException(status_code=500, detail="Failed to confirm settings update.")
            logger.info(f"Appearance settings updated successfully for user: {current_user.email}")

        else:
            logger.info(f"No existing appearance settings found for user {current_user.email}. Creating new document...")
            # Create new: merge input with base defaults
            base_defaults = AppearanceSettingsBase().model_dump(by_alias=True)
            new_settings_data = {**base_defaults, **update_data}
            new_settings = AppearanceSettings(user=current_user, **new_settings_data) # type: ignore
            await new_settings.insert()
            settings_to_return = new_settings
            logger.info(f"Appearance settings created successfully for user: {current_user.email}")

        if not settings_to_return or not settings_to_return.id:
             logger.error(f"Appearance settings ID missing after save/insert for user {current_user.email}")
             raise HTTPException(status_code=500, detail="Failed to retrieve settings ID after update.")

        # Prepare and return response data
        response_data = settings_to_return.model_dump(by_alias=True) # Use by_alias for consistency ('theme')
        # --- FIX APPLIED HERE ---
        # Ensure the '_id' key holds the string representation
        if '_id' in response_data and settings_to_return.id:
             response_data['_id'] = str(settings_to_return.id)
        elif settings_to_return.id: # Fallback
             response_data['_id'] = str(settings_to_return.id)
        # ------------------------
        return AppearanceSettingsRead(**response_data)

    except ValidationError as e: # Catch Pydantic validation errors
        logger.warning(f"Validation error updating appearance settings for user {current_user.email}: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except Exception as e:
        logger.exception(f"Error updating appearance settings for user {current_user.email}:")
        raise HTTPException(status_code=500, detail="Could not update appearance settings.")