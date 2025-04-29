# app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from beanie.exceptions import DocumentNotFound

from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.models.enums import UserType # <-- Import UserType
from app.schemas.token import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    email = decode_access_token(token)
    if email is None:
        print("Token decoding failed or email not found in token.") # Debug log
        raise credentials_exception

    token_data = TokenData(email=email)

    try:
        # Use find_one consistently
        user = await User.find_one(User.email == token_data.email)
        if user is None:
            print(f"User not found in DB for email: {token_data.email}") # Debug log
            raise credentials_exception
        # print(f"User found: {user.email}, Active: {user.is_active}") # Debug log
        return user
    except DocumentNotFound: # Should be caught by find_one returning None, but keep for safety
        print(f"DocumentNotFound exception for email: {token_data.email}") # Debug log
        raise credentials_exception
    except Exception as e: # Catch broader exceptions during DB lookup
        print(f"Error fetching user: {e}")
        raise credentials_exception


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

# --- NEW Dependency: Get Current Admin User ---
async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to get the current active user and verify they are an ADMIN.
    Raises HTTP 403 Forbidden if the user is not an admin.
    """
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted: Requires admin privileges."
        )
    return current_user
# ---------------------------------------------