# app/api/v1/endpoints/user_symbols_customization.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List, Dict

from app.db.models.user import User
from app.db.models.user_symbols import UserCategorySymbol  # New model
from app.schemas.symbols import (  # Assuming schemas are in app.schemas.symbols
    UserAddSymbolPayload,
    UserCustomizedCategoriesResponse,
    UserSymbolData,
    UserSymbolAddedResponse,
)
from app.api.deps import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/customized-categories",
    response_model=UserCustomizedCategoriesResponse,
    summary="Get User's Customized Category Symbols",
    description="Retrieves all symbols added by the currently authenticated user, grouped by category name.",
    tags=["User Symbols Customization"],
)
async def get_user_customized_symbols(
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"Fetching customized category symbols for user: {current_user.email}")
    user_symbols_cursor = UserCategorySymbol.find(UserCategorySymbol.user.id == current_user.id)  # type: ignore

    customized_map: Dict[str, List[UserSymbolData]] = {}
    async for symbol_doc in user_symbols_cursor:
        if symbol_doc.category_name not in customized_map:
            customized_map[symbol_doc.category_name] = []
        customized_map[symbol_doc.category_name].append(
            UserSymbolData(keyword=symbol_doc.keyword)  # Add image_uri if present
        )

    # Sort keywords within each category for consistent output
    for category_keywords in customized_map.values():
        category_keywords.sort(key=lambda s: s.keyword)

    return UserCustomizedCategoriesResponse(customized_symbols=customized_map)


@router.post(
    "/customized-categories/{category_name}/symbols",
    response_model=UserSymbolAddedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a Symbol to a User's Category",
    description="Allows a user to add a symbol keyword to a specific category (standard or new). "
    "This is stored as a user-specific addition.",
    tags=["User Symbols Customization"],
)
async def add_symbol_to_user_category(
    payload: UserAddSymbolPayload,
    current_user: User = Depends(get_current_active_user),
    category_name: str = Path(
        ..., title="Category name (lowercase)", min_length=1, example="food"
    ),
):
    processed_category_name = category_name.lower().strip()
    new_keyword = payload.keyword.strip()

    logger.info(
        f"User '{current_user.email}' attempting to add symbol '{new_keyword}' to their category '{processed_category_name}'."
    )

    if not new_keyword:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Symbol keyword cannot be empty.",
        )

    # Check for duplicates for this user in this category
    existing_symbol = await UserCategorySymbol.find_one(
        UserCategorySymbol.user.id == current_user.id,  # type: ignore
        UserCategorySymbol.category_name == processed_category_name,
        UserCategorySymbol.keyword
        == new_keyword,  # Consider case-insensitivity if needed
    )
    if existing_symbol:
        logger.warning(
            f"User '{current_user.email}' - Symbol '{new_keyword}' already exists in their category '{processed_category_name}'."
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You have already added the symbol '{new_keyword}' to the category '{processed_category_name}'.",
        )

    new_user_symbol = UserCategorySymbol(
        keyword=new_keyword,
        category_name=processed_category_name,
        user=current_user,  # type: ignore
        # image_uri=payload.image_uri # if applicable
    )
    try:
        await new_user_symbol.insert()
        logger.info(
            f"User '{current_user.email}' successfully added symbol '{new_keyword}' to category '{processed_category_name}'. ID: {new_user_symbol.id}"
        )
        return UserSymbolAddedResponse(
            message="Symbol added to your category.",
            category_name=processed_category_name,
            keyword=new_keyword,
            # id=str(new_user_symbol.id)
        )
    except Exception as e:
        logger.exception(
            f"DB error adding symbol for user {current_user.email} to category {processed_category_name}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add symbol.",
        )


# TODO: Implement DELETE endpoint:
# DELETE /customized-categories/{category_name}/symbols/{keyword_or_symbol_id}
