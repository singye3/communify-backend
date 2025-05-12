# app/api/v1/endpoints/settings.py
import logging
from typing import Dict, Any, Optional # Added Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError # For specific Pydantic error handling

from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings
from app.db.models.enums import AsdLevel # Import enums used for conversion

# Assuming schemas are structured to handle aliases if necessary (e.g., for '_id' -> 'id')
# and that Update schemas correctly define optional fields.
from app.schemas.settings import (
    ParentalSettingsRead,
    ParentalSettingsUpdateRequest, # This should model the { "value": { ... } } structure
    ParentalSettingsBase
)
from app.schemas.appearance import (
    AppearanceSettingsRead,
    AppearanceSettingsUpdate, # This is a direct partial update of fields
    AppearanceSettingsBase
)
from app.api.deps import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Helper for Response Preparation ---
def _prepare_settings_read_data(settings_model: Any, model_name: str) -> Dict[str, Any]:
    """
    Converts a settings Beanie model instance (Parental or Appearance)
    to a dictionary suitable for its Pydantic Read schema validation.
    Handles ObjectId for 'id' and converts enums to their string values.
    """
    if not settings_model or not hasattr(settings_model, 'id'):
        logger.error(f"Attempted to prepare {model_name}Read data from an invalid model or model without ID.")
        # This situation implies an issue either in fetching or creating default settings.
        # For GET, we might return defaults. For PATCH, this indicates a problem after an update.
        raise ValueError(f"Cannot prepare response data from invalid {model_name} model.")

    # Use by_alias=True if your Pydantic 'Read' schemas use aliases (e.g., id for _id)
    # and Beanie model_dump doesn't automatically handle it for Pydantic v2 model_validate.
    # For simplicity, we'll assume 'Read' schemas expect direct field names unless aliased.
    response_data = settings_model.model_dump()

    response_data['id'] = str(settings_model.id) # Ensure ID is string

    # Example for ParentalSettings enums (add more as needed per your schema)
    if model_name == "ParentalSettings":
        if 'asd_level' in response_data and isinstance(response_data.get('asd_level'), AsdLevel):
            response_data['asd_level'] = response_data['asd_level'].value
        # Add conversions for other enums like downtime_days if they are enums in the model
        # but expected as lists of strings in the Read schema.

    # Example for AppearanceSettings enums (add more as needed)
    # if model_name == "AppearanceSettings":
    #     if 'symbol_grid_layout' in response_data and isinstance(response_data.get('symbol_grid_layout'), GridLayoutTypeEnum):
    #         response_data['symbol_grid_layout'] = response_data['symbol_grid_layout'].value

    return response_data

# ============================
# PARENTAL SETTINGS
# ============================

@router.get(
    "/parental",
    response_model=ParentalSettingsRead,
    summary="Get Parental Settings",
    tags=["Settings - Parental"]
)
async def read_parental_settings(current_user: User = Depends(get_current_active_user)):
    logger.debug(f"Fetching parental settings for user: {current_user.email}")
    try:
        settings = await ParentalSettings.find_one(ParentalSettings.user.id == current_user.id) # type: ignore

        if not settings:
            logger.info(f"No parental settings for {current_user.email}. Returning defaults.")
            default_data = ParentalSettingsBase().model_dump()
            # Ensure 'id' is present for ParentalSettingsRead, even for defaults
            return ParentalSettingsRead(id="defaults_returned", **default_data)

        prepared_data = _prepare_settings_read_data(settings, "ParentalSettings")
        return ParentalSettingsRead.model_validate(prepared_data)
    except ValidationError as e:
        logger.warning(f"Validation error for ParentalSettingsRead for {current_user.email}: {e.errors()}")
        raise HTTPException(status_code=500, detail="Error processing parental settings.")
    except Exception:
        logger.exception(f"Error fetching parental settings for {current_user.email}")
        raise HTTPException(status_code=500, detail="Could not retrieve parental settings.")


@router.patch(
    "/parental",
    response_model=ParentalSettingsRead,
    summary="Update Parental Settings",
    tags=["Settings - Parental"]
)
async def patch_parental_settings(
    request_body: ParentalSettingsUpdateRequest, # Expects { "value": { ...settings... } }
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"Updating parental settings for user: {current_user.email}")
    logger.debug(f"Full PATCH request body received: {request_body.model_dump(exclude_unset=True)}")


    # Extract the actual settings to update from the 'value' field
    # Ensure exclude_unset=True to only get fields client intended to change
    settings_values_to_update = request_body.value.model_dump(exclude_unset=True)
    logger.debug(f"Values to update extracted from 'value' field: {settings_values_to_update}")


    if not settings_values_to_update: # Check if the 'value' object itself was empty or all its fields were null
        logger.warning(f"No settings data provided in 'value' field by user {current_user.email}.")
        # Fetch and return current settings if no update data in 'value'
        existing_settings = await ParentalSettings.find_one(ParentalSettings.user.id == current_user.id) # type: ignore
        if existing_settings:
            prepared_data = _prepare_settings_read_data(existing_settings, "ParentalSettings")
            return ParentalSettingsRead.model_validate(prepared_data)
        else: # Should not happen if defaults are created during registration
            logger.info(f"No existing parental settings for {current_user.email}, returning defaults.")
            default_data = ParentalSettingsBase().model_dump()
            return ParentalSettingsRead(id="defaults_returned_on_empty_patch", **default_data)

    try:
        existing_settings = await ParentalSettings.find_one(ParentalSettings.user.id == current_user.id) # type: ignore
        settings_to_return: Optional[ParentalSettings] = None

        if existing_settings:
            logger.debug(f"Found existing parental settings for {current_user.email}. Updating.")
            # Beanie's update with $set handles partial updates well.
            # Pydantic model for settings_values_to_update ensures valid fields and types.
            await existing_settings.update({"$set": settings_values_to_update})
            settings_to_return = await ParentalSettings.get(existing_settings.id) # type: ignore Fetch fresh data
            if not settings_to_return: # Should not happen if update was successful
                logger.error(f"Failed to re-fetch parental settings after update for {current_user.email}")
                raise HTTPException(status_code=500, detail="Error confirming settings update.")
            logger.info(f"Parental settings updated for {current_user.email}.")
        else:
            # This case means default ParentalSettings were not created on user registration.
            # For PATCH, typically you update an existing resource.
            # If you intend PATCH to create if not exists (upsert):
            logger.info(f"No parental settings for {current_user.email}. Creating new with PATCH data.")
            # Merge update data with base defaults for a complete new document
            base_data = ParentalSettingsBase().model_dump()
            merged_data = {**base_data, **settings_values_to_update}
            new_settings = ParentalSettings(user=current_user, **merged_data) # type: ignore
            settings_to_return = await new_settings.insert()
            if not settings_to_return: # Should not happen if insert was successful
                logger.error(f"Failed to insert new parental settings for {current_user.email}")
                raise HTTPException(status_code=500, detail="Error creating new settings.")
            logger.info(f"Parental settings created via PATCH for {current_user.email}.")

        if not settings_to_return: # Should be caught by earlier checks
             raise HTTPException(status_code=500, detail="Failed to obtain settings after operation.")

        prepared_data = _prepare_settings_read_data(settings_to_return, "ParentalSettings")
        return ParentalSettingsRead.model_validate(prepared_data)

    except ValidationError as e:
        logger.warning(f"Pydantic validation error processing parental settings for {current_user.email}: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except Exception:
        logger.exception(f"Error updating parental settings for {current_user.email}")
        raise HTTPException(status_code=500, detail="Could not update parental settings.")


# ============================
# APPEARANCE SETTINGS
# ============================

@router.get(
    "/appearance",
    response_model=AppearanceSettingsRead,
    summary="Get Appearance Settings",
    tags=["Settings - Appearance"]
)
async def read_appearance_settings(current_user: User = Depends(get_current_active_user)):
    logger.debug(f"Fetching appearance settings for user: {current_user.email}")
    try:
        settings = await AppearanceSettings.find_one(AppearanceSettings.user.id == current_user.id) # type: ignore

        if not settings:
            logger.info(f"No appearance settings for {current_user.email}. Returning defaults.")
            default_data = AppearanceSettingsBase().model_dump()
            return AppearanceSettingsRead(id="defaults_returned", **default_data)

        prepared_data = _prepare_settings_read_data(settings, "AppearanceSettings")
        return AppearanceSettingsRead.model_validate(prepared_data)
    except ValidationError as e:
        logger.warning(f"Validation error for AppearanceSettingsRead for {current_user.email}: {e.errors()}")
        raise HTTPException(status_code=500, detail="Error processing appearance settings.")
    except Exception:
        logger.exception(f"Error fetching appearance settings for {current_user.email}")
        raise HTTPException(status_code=500, detail="Could not retrieve appearance settings.")


@router.patch(
    "/appearance",
    response_model=AppearanceSettingsRead,
    summary="Update Appearance Settings",
    tags=["Settings - Appearance"]
)
async def patch_appearance_settings(
    settings_in: AppearanceSettingsUpdate, # Direct partial update of fields
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"Updating appearance settings for user: {current_user.email}")
    
    # For this endpoint, settings_in directly contains the fields to update (e.g., { "font_size": "large" })
    update_data = settings_in.model_dump(exclude_unset=True)
    logger.debug(f"Update data received for appearance settings: {update_data}")

    if not update_data:
        logger.warning(f"No appearance settings data provided by user {current_user.email}.")
        existing_settings = await AppearanceSettings.find_one(AppearanceSettings.user.id == current_user.id) # type: ignore
        if existing_settings:
            prepared_data = _prepare_settings_read_data(existing_settings, "AppearanceSettings")
            return AppearanceSettingsRead.model_validate(prepared_data)
        else:
            logger.info(f"No existing appearance settings for {current_user.email}, returning defaults.")
            default_data = AppearanceSettingsBase().model_dump()
            return AppearanceSettingsRead(id="defaults_returned_on_empty_patch", **default_data)

    try:
        existing_settings = await AppearanceSettings.find_one(AppearanceSettings.user.id == current_user.id) # type: ignore
        settings_to_return: Optional[AppearanceSettings] = None

        if existing_settings:
            logger.debug(f"Found existing appearance settings for {current_user.email}. Updating.")
            await existing_settings.update({"$set": update_data})
            settings_to_return = await AppearanceSettings.get(existing_settings.id) # type: ignore
            if not settings_to_return:
                logger.error(f"Failed to re-fetch appearance settings after update for {current_user.email}")
                raise HTTPException(status_code=500, detail="Error confirming settings update.")
            logger.info(f"Appearance settings updated for {current_user.email}.")
        else:
            logger.info(f"No appearance settings for {current_user.email}. Creating new with PATCH data.")
            base_data = AppearanceSettingsBase().model_dump()
            merged_data = {**base_data, **update_data}
            new_settings = AppearanceSettings(user=current_user, **merged_data) # type: ignore
            settings_to_return = await new_settings.insert()
            if not settings_to_return:
                logger.error(f"Failed to insert new appearance settings for {current_user.email}")
                raise HTTPException(status_code=500, detail="Error creating new settings.")
            logger.info(f"Appearance settings created via PATCH for {current_user.email}.")
        
        if not settings_to_return:
             raise HTTPException(status_code=500, detail="Failed to obtain settings after operation.")

        prepared_data = _prepare_settings_read_data(settings_to_return, "AppearanceSettings")
        return AppearanceSettingsRead.model_validate(prepared_data)

    except ValidationError as e:
        logger.warning(f"Pydantic validation error processing appearance settings for {current_user.email}: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except Exception:
        logger.exception(f"Error updating appearance settings for {current_user.email}")
        raise HTTPException(status_code=500, detail="Could not update appearance settings.")