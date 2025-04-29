# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from beanie.exceptions import DocumentNotFound

from app.core.security import create_access_token, verify_password, get_password_hash
from app.db.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from app.api.deps import get_current_active_user

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = await User.find_one(User.email == form_data.username)
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

        access_token = create_access_token(subject=user.email)
        return {"access_token": access_token, "token_type": "bearer"}
    except DocumentNotFound:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate):
    existing_user = await User.find_one(User.email == user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    hashed_password = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        name=user_in.name,
        hashed_password=hashed_password
    )
    inserted_user = await user.insert()
    if not inserted_user or not inserted_user.id:
         raise HTTPException(status_code=500, detail="Failed to retrieve user ID after insertion.")


    user_read_data = {
        "id": str(inserted_user.id), 
        "email": inserted_user.email,
        "name": inserted_user.name,
        "avatar_uri": inserted_user.avatar_uri,
        "is_active": inserted_user.is_active,
        "created_at": inserted_user.created_at,
        "updated_at": inserted_user.updated_at
    }
    # ------------------------------------------

    # Pass the prepared dictionary to UserRead
    return UserRead(**user_read_data)