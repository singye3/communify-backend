# app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from beanie.exceptions import DocumentNotFound

from app.core.security import decode_access_token
from app.db.models.user import User
from app.schemas.token import TokenData

# Define the OAuth2 scheme
# tokenUrl should point to your actual login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    email = decode_access_token(token)
    if email is None:
        raise credentials_exception

    token_data = TokenData(email=email)

    try:
        user = await User.find_one(User.email == token_data.email)
        if user is None:
            raise credentials_exception
        return user
    except DocumentNotFound:
        raise credentials_exception


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user