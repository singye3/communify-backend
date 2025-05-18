# app/api/deps.py
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from beanie.exceptions import (
    DocumentNotFound,
)  # Keep if User.get might raise it, though less common
from pydantic import ValidationError  # For TokenData validation

from app.core.config import settings

# decode_access_token should now be designed to return the subject (user_id string)
from app.core.security import (
    decode_access_token,
)  # Assumes this function now returns the user_id string or raises error
from app.db.models.user import User
from app.db.models.enums import UserType  # Keep for get_current_admin_user
from app.schemas.token import TokenData  # This schema should now expect user_id

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token",  # Ensure settings.API_V1_STR is correct
    description="OAuth2 Password Bearer flow",
    auto_error=True,  # If True, FastAPI will automatically return 401 if token is missing/invalid
)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get the current user from a validated JWT token.
    The token's subject ('sub' claim) is expected to be the user's ID.
    Handles token decoding and database lookup by ID.

    Raises HTTPException 401 if token is invalid, expired, or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    logger.debug("get_current_user: Attempting to decode token and extract user ID.")

    # decode_access_token should return the user_id (subject) from the token payload
    # or raise an appropriate exception (e.g., JWTError, or the credentials_exception directly)
    user_id_from_token = decode_access_token(token)

    if (
        user_id_from_token is None
    ):  # Should be handled by decode_access_token raising an error
        logger.warning(
            "get_current_user: Token decoding failed or subject (user_id) was missing."
        )
        raise credentials_exception

    try:
        # Validate that the extracted subject is a valid user_id for TokenData
        # TokenData now expects user_id
        token_data = TokenData(user_id=user_id_from_token)
        logger.debug(
            f"get_current_user: Token decoded, subject (user_id): {token_data.user_id}"
        )
    except ValidationError as e:
        logger.warning(
            f"get_current_user: TokenData validation failed for user_id '{user_id_from_token}': {e}"
        )
        raise credentials_exception

    # At this point, token_data.user_id should be the string representation of the user's ObjectId
    if (
        not token_data.user_id
    ):  # Should have been caught by decode_access_token or TokenData validation
        logger.error(
            "get_current_user: Critical - user_id is None/empty after token processing."
        )
        raise credentials_exception

    try:
        logger.debug(
            f"get_current_user: Attempting database lookup for user ID: {token_data.user_id}"
        )
        # Fetch user by ID using Beanie's .get() method.
        # Beanie's .get() can typically handle string representations of ObjectIds.
        user = await User.get(token_data.user_id)

        if user is None:
            logger.warning(
                f"get_current_user: User with ID '{token_data.user_id}' from token not found in database."
            )
            raise credentials_exception

        logger.debug(
            f"get_current_user: User '{user.email}' (ID: {user.id}) found in database."
        )
        return user

    except Exception as e:  # Catch any other unexpected errors during DB lookup
        logger.error(
            f"get_current_user: Database or unexpected error during user lookup for ID {token_data.user_id}: {e}",
            exc_info=True,
        )
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to ensure the user fetched by get_current_user is active.
    Raises HTTPException 400 if the user is inactive.
    """
    logger.debug(
        f"get_current_active_user: Checking active status for user: {current_user.email} (ID: {current_user.id})"
    )
    if not current_user.is_active:
        logger.warning(
            f"get_current_active_user: User '{current_user.email}' (ID: {current_user.id}) is inactive. Access denied."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,  # Or 403 Forbidden
            detail="Inactive user",
        )
    logger.debug(
        f"get_current_active_user: User '{current_user.email}' (ID: {current_user.id}) is active."
    )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Dependency to ensure the current active user has the ADMIN role.
    Raises HTTPException 403 if the user is not an admin.
    """
    logger.debug(
        f"get_current_admin_user: Checking admin status for user: {current_user.email} (ID: {current_user.id})"
    )
    if current_user.user_type != UserType.ADMIN:
        logger.warning(
            f"get_current_admin_user: User '{current_user.email}' (ID: {current_user.id}, type: {current_user.user_type}) attempted admin action. Access denied."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted: Requires admin privileges.",
        )
    logger.debug(
        f"get_current_admin_user: User '{current_user.email}' (ID: {current_user.id}) is ADMIN. Access granted."
    )
    return current_user
