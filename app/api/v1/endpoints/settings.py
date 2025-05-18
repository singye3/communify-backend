# app/api/v1/endpoints/settings.py
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings
from app.db.models.enums import (
    AsdLevel as AsdLevelEnum,
    DayOfWeek as DayOfWeekEnum,
    GridLayoutTypeEnum,
)

# Corrected import from app.schemas.settings
from app.schemas.settings import (
    ParentalSettingsRead,
    ParentalSettingsFieldsForUpdate,  # CORRECTED: Was ParentalSettingsValueUpdate
    ParentalSettingsUpdateRequest,
    ParentalSettingsBase,
)
from app.schemas.appearance import (
    AppearanceSettingsRead,
    AppearanceSettingsUpdate,
    AppearanceSettingsBase,
)
from app.api.deps import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Helper for Response Preparation ---
# (Keep _prepare_settings_read_data as it was)
def _prepare_settings_read_data(settings_model: Any, model_name: str) -> Dict[str, Any]:
    # ... (implementation from previous correct version) ...
    if not settings_model:
        logger.error(f"Attempted to prepare {model_name}Read data from a None model.")
        raise ValueError(
            f"Cannot prepare response data from invalid {model_name} model."
        )
    response_data = settings_model.model_dump(by_alias=False)
    if hasattr(settings_model, "id") and settings_model.id is not None:
        response_data["id"] = str(settings_model.id)
    elif "id" in response_data and response_data["id"] is not None:
        response_data["id"] = str(response_data["id"])
    if model_name == "ParentalSettings":
        if "asd_level" in response_data and isinstance(
            response_data.get("asd_level"), AsdLevelEnum
        ):
            response_data["asd_level"] = response_data["asd_level"].value
        elif response_data.get("asd_level") is None:
            response_data["asd_level"] = None
        if "downtime_days" in response_data and isinstance(
            response_data.get("downtime_days"), list
        ):
            new_downtime_days = []
            for day_enum_val in response_data["downtime_days"]:
                if isinstance(day_enum_val, DayOfWeekEnum):
                    new_downtime_days.append(day_enum_val.value)
                elif isinstance(day_enum_val, str):
                    try:
                        DayOfWeekEnum(day_enum_val)
                        new_downtime_days.append(day_enum_val)
                    except ValueError:
                        logger.warning(
                            f"Invalid DayOfWeek string '{day_enum_val}' in DB."
                        )
            response_data["downtime_days"] = new_downtime_days
    elif model_name == "AppearanceSettings":
        if "symbol_grid_layout" in response_data and isinstance(
            response_data.get("symbol_grid_layout"), GridLayoutTypeEnum
        ):
            response_data["symbol_grid_layout"] = response_data[
                "symbol_grid_layout"
            ].value
    return response_data


# ============================
# PARENTAL SETTINGS
# (Keep this section as it was in the previous correct version,
#  ensure it uses ParentalSettingsFieldsForUpdate where appropriate if any local var was named ParentalSettingsValueUpdate)
# ============================
@router.get(
    "/parental",
    response_model=ParentalSettingsRead,
    summary="Get Parental Settings",
    tags=["Settings - Parental"],
)
async def read_parental_settings(current_user: User = Depends(get_current_active_user)):
    # ... (implementation from previous correct version) ...
    logger.debug(f"Fetching parental settings for user: {current_user.email}")
    try:
        settings = await ParentalSettings.find_one(ParentalSettings.user.id == current_user.id)  # type: ignore
        if not settings:
            logger.info(
                f"No parental settings for {current_user.email}. Creating and returning defaults."
            )
            default_data_for_db = ParentalSettingsBase().model_dump()
            settings_dict_for_create = {"user": current_user, **default_data_for_db}
            settings = ParentalSettings(**settings_dict_for_create)  # type: ignore
            await settings.insert()
            logger.info(f"Default parental settings created for {current_user.email}.")
        prepared_data = _prepare_settings_read_data(settings, "ParentalSettings")
        return ParentalSettingsRead.model_validate(prepared_data)
    except ValidationError as e:
        logger.error(
            f"Validation error creating ParentalSettingsRead response for {current_user.email}: {e.errors()}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal error processing parental settings response.",
        )
    except Exception:
        logger.exception(f"Error fetching parental settings for {current_user.email}")
        raise HTTPException(
            status_code=500, detail="Could not retrieve parental settings."
        )


@router.patch(
    "/parental",
    response_model=ParentalSettingsRead,
    summary="Update Parental Settings",
    tags=["Settings - Parental"],
)
async def patch_parental_settings(
    request_body: ParentalSettingsUpdateRequest,  # This already uses ParentalSettingsFieldsForUpdate internally for its 'value' field
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"Updating parental settings for user: {current_user.email}")
    # request_body.value is of type ParentalSettingsFieldsForUpdate (which contains optional fields)
    settings_values_to_update = request_body.value.model_dump(exclude_unset=True)
    logger.debug(f"Values to update from 'value' field: {settings_values_to_update}")

    if not settings_values_to_update:
        logger.warning(
            f"No settings data in 'value' field by {current_user.email}. Returning current settings."
        )
        existing_settings = await ParentalSettings.find_one(ParentalSettings.user.id == current_user.id)  # type: ignore
        if not existing_settings:
            default_data = ParentalSettingsBase().model_dump()
            settings_dict_for_create = {"user": current_user, **default_data}
            existing_settings = ParentalSettings(**settings_dict_for_create)  # type: ignore
            await existing_settings.insert()
        prepared_data = _prepare_settings_read_data(
            existing_settings, "ParentalSettings"
        )
        return ParentalSettingsRead.model_validate(prepared_data)
    try:
        settings_doc = await ParentalSettings.find_one(ParentalSettings.user.id == current_user.id)  # type: ignore
        if not settings_doc:
            logger.info(
                f"No parental settings for {current_user.email}. Creating new with PATCH data."
            )
            base_data = ParentalSettingsBase().model_dump()
            merged_data_for_create = {**base_data, **settings_values_to_update}
            settings_dict_for_create = {"user": current_user, **merged_data_for_create}
            new_settings = ParentalSettings(**settings_dict_for_create)  # type: ignore
            await new_settings.insert()
            settings_doc = new_settings
            logger.info(
                f"Parental settings created via PATCH for {current_user.email}."
            )
        else:
            logger.debug(
                f"Found existing parental settings for {current_user.email}. Updating."
            )
            await settings_doc.update({"$set": settings_values_to_update})
            settings_doc = await ParentalSettings.get(settings_doc.id)  # type: ignore
            if not settings_doc:
                logger.error(
                    f"Failed to re-fetch parental settings after update for {current_user.email}"
                )
                raise HTTPException(
                    status_code=500, detail="Error confirming settings update."
                )
            logger.info(f"Parental settings updated for {current_user.email}.")
        prepared_data = _prepare_settings_read_data(settings_doc, "ParentalSettings")
        return ParentalSettingsRead.model_validate(prepared_data)
    except ValidationError as e:
        logger.error(
            f"Pydantic validation error constructing response for {current_user.email}: {e.errors()}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error processing settings response.",
        )
    except Exception:
        logger.exception(
            f"General error updating parental settings for {current_user.email}"
        )
        raise HTTPException(
            status_code=500, detail="Could not update parental settings."
        )


# ============================
# APPEARANCE SETTINGS
# (Keep this section as it was in the previous correct version)
# ============================
@router.get(
    "/appearance",
    response_model=AppearanceSettingsRead,
    summary="Get Appearance Settings",
    tags=["Settings - Appearance"],
)
async def read_appearance_settings(
    current_user: User = Depends(get_current_active_user),
):
    # ... (implementation from previous correct version) ...
    logger.debug(f"Fetching appearance settings for user: {current_user.email}")
    try:
        settings = await AppearanceSettings.find_one(AppearanceSettings.user.id == current_user.id)  # type: ignore
        if not settings:
            logger.info(
                f"No appearance settings for {current_user.email}. Creating and returning defaults."
            )
            default_data_for_db = AppearanceSettingsBase().model_dump()
            settings_dict_for_create = {"user": current_user, **default_data_for_db}
            settings = AppearanceSettings(**settings_dict_for_create)  # type: ignore
            await settings.insert()
            logger.info(
                f"Default appearance settings created for {current_user.email}."
            )
        prepared_data = _prepare_settings_read_data(settings, "AppearanceSettings")
        return AppearanceSettingsRead.model_validate(prepared_data)
    except ValidationError as e:
        logger.error(
            f"Validation error creating AppearanceSettingsRead response for {current_user.email}: {e.errors()}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal error processing appearance settings response.",
        )
    except Exception:
        logger.exception(f"Error fetching appearance settings for {current_user.email}")
        raise HTTPException(
            status_code=500, detail="Could not retrieve appearance settings."
        )


@router.patch(
    "/appearance",
    response_model=AppearanceSettingsRead,
    summary="Update Appearance Settings",
    tags=["Settings - Appearance"],
)
async def patch_appearance_settings(
    settings_in: AppearanceSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
):
    # ... (implementation from previous correct version) ...
    logger.info(f"Updating appearance settings for user: {current_user.email}")
    update_data = settings_in.model_dump(exclude_unset=True)
    logger.debug(f"Update data for appearance settings: {update_data}")
    if not update_data:
        logger.warning(
            f"No appearance settings data provided by {current_user.email}. Returning current."
        )
        existing_settings = await AppearanceSettings.find_one(AppearanceSettings.user.id == current_user.id)  # type: ignore
        if not existing_settings:
            default_data = AppearanceSettingsBase().model_dump()
            settings_dict_for_create = {"user": current_user, **default_data}
            existing_settings = AppearanceSettings(**settings_dict_for_create)  # type: ignore
            await existing_settings.insert()
        prepared_data = _prepare_settings_read_data(
            existing_settings, "AppearanceSettings"
        )
        return AppearanceSettingsRead.model_validate(prepared_data)
    try:
        settings_doc = await AppearanceSettings.find_one(AppearanceSettings.user.id == current_user.id)  # type: ignore
        if not settings_doc:
            logger.info(
                f"No appearance settings for {current_user.email}. Creating new with PATCH data."
            )
            base_data = AppearanceSettingsBase().model_dump()
            merged_data_for_create = {**base_data, **update_data}
            settings_dict_for_create = {"user": current_user, **merged_data_for_create}
            new_settings = AppearanceSettings(**settings_dict_for_create)  # type: ignore
            await new_settings.insert()
            settings_doc = new_settings
            logger.info(
                f"Appearance settings created via PATCH for {current_user.email}."
            )
        else:
            logger.debug(
                f"Found existing appearance settings for {current_user.email}. Updating."
            )
            await settings_doc.update({"$set": update_data})
            settings_doc = await AppearanceSettings.get(settings_doc.id)  # type: ignore
            if not settings_doc:
                logger.error(
                    f"Failed to re-fetch appearance settings after update for {current_user.email}"
                )
                raise HTTPException(
                    status_code=500, detail="Error confirming settings update."
                )
            logger.info(f"Appearance settings updated for {current_user.email}.")
        prepared_data = _prepare_settings_read_data(settings_doc, "AppearanceSettings")
        return AppearanceSettingsRead.model_validate(prepared_data)
    except ValidationError as e:
        logger.error(
            f"Pydantic validation error constructing response for {current_user.email}: {e.errors()}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error processing settings response.",
        )
    except Exception:
        logger.exception(f"Error updating appearance settings for {current_user.email}")
        raise HTTPException(
            status_code=500, detail="Could not update appearance settings."
        )
