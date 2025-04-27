# app/api/v1/endpoints/settings.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from app.db.models.user import User
from app.db.models.settings import ParentalSettings
from app.db.models.appearance_settings import AppearanceSettings # Import Appearance model
from app.schemas.settings import ParentalSettingsRead, ParentalSettingsUpdate, ParentalSettingsBase # Keep Parental schemas
from app.schemas.appearance import AppearanceSettingsRead, AppearanceSettingsUpdate, AppearanceSettingsBase # Import Appearance schemas
from app.api.deps import get_current_active_user

router = APIRouter()

# --- Parental Settings Routes ---

@router.get("/parental", response_model=ParentalSettingsRead, tags=["Parental Settings"])
async def read_parental_settings(current_user: User = Depends(get_current_active_user)):
    settings = await ParentalSettings.find_one(ParentalSettings.user.id == current_user.id) # type: ignore
    if not settings:
        # Return default parental settings if none exist
        default_data = ParentalSettingsBase().model_dump()
        return ParentalSettingsRead(id="default", **default_data)
    return ParentalSettingsRead(**settings.model_dump(by_alias=True))

@router.put("/parental", response_model=ParentalSettingsRead, tags=["Parental Settings"])
async def update_parental_settings(
    settings_in: ParentalSettingsUpdate,
    current_user: User = Depends(get_current_active_user)
):
    existing_settings = await ParentalSettings.find_one(ParentalSettings.user.id == current_user.id) # type: ignore
    if existing_settings:
        update_data = settings_in.model_dump(exclude_unset=True)
        for field, value in update_data.items(): setattr(existing_settings, field, value)
        await existing_settings.save()
        return ParentalSettingsRead(**existing_settings.model_dump(by_alias=True))
    else:
        new_settings = ParentalSettings(user=current_user, **settings_in.model_dump()) # type: ignore
        await new_settings.insert()
        return ParentalSettingsRead(**new_settings.model_dump(by_alias=True))

# --- Appearance Settings Routes ---

@router.get("/appearance", response_model=AppearanceSettingsRead, tags=["Appearance Settings"])
async def read_appearance_settings(current_user: User = Depends(get_current_active_user)):
    settings = await AppearanceSettings.find_one(AppearanceSettings.user.id == current_user.id) # type: ignore
    if not settings:
        # Return default appearance settings if none exist
        default_data = AppearanceSettingsBase().model_dump()
        return AppearanceSettingsRead(id="default", **default_data)
    return AppearanceSettingsRead(**settings.model_dump(by_alias=True))

@router.put("/appearance", response_model=AppearanceSettingsRead, tags=["Appearance Settings"])
async def update_appearance_settings(
    settings_in: AppearanceSettingsUpdate,
    current_user: User = Depends(get_current_active_user)
):
    existing_settings = await AppearanceSettings.find_one(AppearanceSettings.user.id == current_user.id) # type: ignore
    if existing_settings:
        update_data = settings_in.model_dump(exclude_unset=True)
        for field, value in update_data.items(): setattr(existing_settings, field, value)
        await existing_settings.save()
        return AppearanceSettingsRead(**existing_settings.model_dump(by_alias=True))
    else:
        new_settings = AppearanceSettings(user=current_user, **settings_in.model_dump()) # type: ignore
        await new_settings.insert()
        return AppearanceSettingsRead(**new_settings.model_dump(by_alias=True))