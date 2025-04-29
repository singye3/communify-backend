# app/api/deps.py
import logging
import traceback # For detailed exception logging
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from beanie.exceptions import DocumentNotFound

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.models.enums import UserType
from app.schemas.token import TokenData

# Get a logger instance for this module
logger = logging.getLogger(__name__)

# OAuth2 scheme definition for dependency injection and security definitions
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token", # Points to the login endpoint
    description="OAuth2 Password Bearer flow",
    auto_error=True # Let FastAPI handle 401 if token is missing/malformed header
)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get the current user from a validated JWT token.
    Handles token decoding and database lookup.

    Raises HTTPException 401 if token is invalid, expired, or user not found/inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials", # Keep detail generic for security
        headers={"WWW-Authenticate": "Bearer"},
    )

    logger.debug("Attempting to get current user from token.")
    email = decode_access_token(token) # security.py now handles detailed logging

    if email is None:
        logger.warning("Token decoding failed or subject (email) was missing.")
        raise credentials_exception

    token_data = TokenData(email=email)
    logger.debug("Token decoded successfully for subject: %s", token_data.email)

    try:
        logger.debug("Attempting database lookup for user: %s", token_data.email)
        # Find the user based on the email from the token
        user = await User.find_one(User.email == token_data.email)

        if user is None:
            # This case is important: Token is valid, but user doesn't exist anymore
            logger.warning("User '%s' from valid token not found in database.", token_data.email)
            raise credentials_exception

        logger.debug("User '%s' found in database.", token_data.email)
        return user

    except Exception as e:
        # Catch potential DB errors during the lookup
        logger.error("Database error during user lookup for email %s: %s", token_data.email, e, exc_info=True)
        # Include traceback in logs for unexpected errors
        # traceback.print_exc() # logger.exception does this with exc_info=True
        raise credentials_exception # Don't expose DB errors directly


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to ensure the user fetched by get_current_user is active.

    Raises HTTPException 400 if the user is inactive.
    """
    logger.debug("Checking active status for user: %s", current_user.email)
    if not current_user.is_active:
        logger.warning("User '%s' is inactive. Access denied.", current_user.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user" # Keep detail somewhat generic
        )
    logger.debug("User '%s' is active.", current_user.email)
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to ensure the current active user has the ADMIN role.

    Raises HTTPException 403 if the user is not an admin.
    """
    logger.debug("Checking admin status for user: %s", current_user.email)
    if current_user.user_type != UserType.ADMIN:
        logger.warning(
            "User '%s' (type: %s) attempted admin action. Access denied.",
            current_user.email, current_user.user_type
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted: Requires admin privileges."
        )
    logger.debug("User '%s' is ADMIN. Access granted.", current_user.email)
    return current_user