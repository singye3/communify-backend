# app/core/security.py
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    logger.info("Passlib password hashing context created successfully using bcrypt.")
except Exception as e:
    logger.critical("CRITICAL ERROR: Failed to initialize password context: %s", e, exc_info=True)
    pwd_context = None 

# --- JWT Settings ---
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
SECRET_KEY = settings.SECRET_KEY

# --- JWT Functions ---

def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generates a JWT access token.

    Args:
        subject: The subject of the token (typically user ID or email).
        expires_delta: Optional timedelta object for custom expiration.
                       If None, uses ACCESS_TOKEN_EXPIRE_MINUTES from settings.

    Returns:
        The encoded JWT access token string.

    Raises:
        RuntimeError: If JWT encoding fails.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)} # Ensure subject is a string

    logger.debug("Creating JWT token for subject '%s' expiring at %s", subject, expire.isoformat())

    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.debug("JWT token created successfully.")
        return encoded_jwt
    except Exception as e:
        logger.critical("Failed to encode JWT token: %s", e, exc_info=True)
        raise RuntimeError("Could not create access token") from e


def decode_access_token(token: str) -> Optional[str]:
    """
    Decodes a JWT access token and validates it.

    Args:
        token: The JWT token string to decode.

    Returns:
        The subject (email) from the token payload if valid and not expired,
        otherwise None.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        subject: Optional[str] = payload.get("sub")

        if subject is None:
            logger.warning("Token decoding failed: 'sub' claim missing.")
            return None
        logger.debug("Token decoded successfully for subject: %s", subject)
        return subject

    except JWTError as e:
        logger.warning("JWT validation/decode error: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error during token decoding: %s", e, exc_info=True)
        return None

# --- Password Functions ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a stored hash.

    Args:
        plain_password: The password entered by the user.
        hashed_password: The hash stored in the database.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    if not pwd_context:
        logger.error("Cannot verify password: Password context not initialized.")
        return False
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.debug("Password verification result: %s", is_valid)
        return is_valid
    except ValueError as e:
        logger.error("Password verification error (likely malformed hash): %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error during password verification: %s", e, exc_info=True)
        return False

def get_password_hash(password: str) -> str:
    """
    Generates a bcrypt hash for a given password.

    Args:
        password: The plain text password to hash.

    Returns:
        The generated password hash string.

    Raises:
        RuntimeError: If the password hashing context is not available.
        Exception: If hashing fails for other reasons.
    """
    if not pwd_context:
        logger.critical("Cannot hash password: Password context not initialized.")
        raise RuntimeError("Password hashing is not available.")
    try:
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed successfully.")
        return hashed
    except Exception as e:
        logger.critical("Failed to hash password: %s", e, exc_info=True)
        raise