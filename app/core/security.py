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
    logger.info(
        "Passlib password hashing context (pwd_context) initialized successfully using bcrypt."
    )
except Exception as e:
    logger.critical(
        "CRITICAL ERROR: Failed to initialize password context (pwd_context): %s",
        e,
        exc_info=True,
    )
    pwd_context = None

ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
RAW_SECRET_KEY_FROM_CONFIG = settings.SECRET_KEY

logger.info(
    f"Raw SECRET_KEY from config: '{RAW_SECRET_KEY_FROM_CONFIG}' (Type: {type(RAW_SECRET_KEY_FROM_CONFIG).__name__})"
)

SECRET_KEY_RUNTIME: Optional[str] = None

if (
    isinstance(RAW_SECRET_KEY_FROM_CONFIG, str)
    and len(RAW_SECRET_KEY_FROM_CONFIG) >= 32
):
    SECRET_KEY_RUNTIME = RAW_SECRET_KEY_FROM_CONFIG
    logger.info(
        f"JWT SECRET_KEY loaded and validated successfully (length: {len(SECRET_KEY_RUNTIME)})."
    )
else:
    logger.critical(
        "CRITICAL SECURITY RISK: SECRET_KEY is not a string, is empty, or is too short (recommended min 32 chars for HS256). "
        f"Actual value (type: {type(RAW_SECRET_KEY_FROM_CONFIG).__name__}): '{str(RAW_SECRET_KEY_FROM_CONFIG)[:10]}...'. "
        "Application JWT functionality will be disabled. Please set a strong SECRET_KEY environment variable."
    )

def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    if not SECRET_KEY_RUNTIME:
        logger.critical(
            "JWT Secret Key is not properly configured (runtime check). Cannot create access token."
        )
        raise RuntimeError("JWT Secret Key is not configured (runtime check).")
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    logger.debug(
        "Creating JWT token for subject '%s' expiring at %s",
        subject,
        expire.isoformat(),
    )
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY_RUNTIME, algorithm=ALGORITHM)
        logger.debug("JWT token created successfully.")
        return encoded_jwt
    except Exception as e:
        logger.critical(
            "Failed to encode JWT token: %s. SECRET_KEY_RUNTIME type: %s",
            e,
            type(SECRET_KEY_RUNTIME).__name__,
            exc_info=True,
        )
        raise RuntimeError(
            "Could not create access token due to an encoding error."
        ) from e

def decode_access_token(token: str) -> Optional[str]:
    if not SECRET_KEY_RUNTIME:
        logger.error(
            "JWT Secret Key is not properly configured (runtime check). Cannot decode access token."
        )
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY_RUNTIME, algorithms=[ALGORITHM])
        subject: Optional[str] = payload.get("sub")
        if subject is None:
            logger.warning("Token decoding failed: 'sub' claim missing in payload.")
            return None
        logger.debug("Token decoded successfully for subject: %s", subject)
        return subject
    except JWTError as e:
        logger.warning("JWT validation/decode error: %s. Token: %s...", e, token[:30])
        return None
    except Exception as e:
        logger.error("Unexpected error during token decoding: %s", e, exc_info=True)
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not pwd_context:
        logger.error(
            "Cannot verify user password: Password context (pwd_context) not initialized."
        )
        return False
    if not plain_password or not hashed_password:
        logger.warning(
            "Attempted to verify password with empty plain_password or hashed_password."
        )
        return False
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.debug("User password verification result: %s", is_valid)
        return is_valid
    except ValueError as e:
        logger.error("User password verification error (likely malformed hash): %s", e)
        return False
    except Exception as e:
        logger.error(
            "Unexpected error during user password verification: %s", e, exc_info=True
        )
        return False

def get_password_hash(password: str) -> str:
    if not pwd_context:
        logger.critical(
            "Cannot hash user password: Password context (pwd_context) not initialized."
        )
        raise RuntimeError("Password hashing service is not available.")
    if not password:
        logger.error("Attempted to hash an empty password.")
        raise ValueError("Password cannot be empty.")
    try:
        hashed = pwd_context.hash(password)
        logger.debug("User password hashed successfully.")
        return hashed
    except Exception as e:
        logger.critical("Failed to hash user password: %s", e, exc_info=True)
        raise RuntimeError("Could not hash password due to an internal error.") from e

def verify_parental_passcode(plain_passcode: str, hashed_passcode: str) -> bool:
    if not pwd_context:
        logger.error(
            "Cannot verify parental passcode: Password context (pwd_context) not initialized."
        )
        return False
    if not plain_passcode or not hashed_passcode:
        logger.warning(
            "Attempted to verify parental passcode with empty plain_passcode or hashed_passcode."
        )
        return False
    try:
        is_valid = pwd_context.verify(plain_passcode, hashed_passcode)
        logger.debug("Parental passcode verification result: %s", is_valid)
        return is_valid
    except ValueError as e:
        logger.error(
            "Parental passcode verification error (likely malformed admits): %s", e
        )
        return False
    except Exception as e:
        logger.error(
            "Unexpected error during parental passcode verification: %s",
            e,
            exc_info=True,
        )
        return False

def get_parental_passcode_hash(passcode: str) -> str:
    if not pwd_context:
        logger.critical(
            "Cannot hash parental passcode: Password context (pwd_context) not initialized."
        )
        raise RuntimeError("Passcode hashing service is not available.")
    if not passcode:
        logger.error("Attempted to hash an empty parental passcode.")
        raise ValueError("Parental passcode cannot be empty.")
    try:
        hashed = pwd_context.hash(passcode)
        logger.debug("Parental passcode hashed successfully.")
        return hashed
    except Exception as e:
        logger.critical("Failed to hash parental passcode: %s", e, exc_info=True)
        raise RuntimeError(
            "Could not hash parental passcode due to an internal error."
        ) from e