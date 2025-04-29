# app/api/v1/endpoints/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List # Import List if returning multiple users later

from app.db.models.user import User
from app.db.models.enums import UserType
from app.schemas.user import UserCreate, UserRead # Re-use UserCreate for input, UserRead for output
from app.core.security import get_password_hash
from app.api.deps import get_current_admin_user # Use the new admin dependency

router = APIRouter()

@router.post(
    "/users/create_admin",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Admin User",
    description="Allows an authenticated Admin user to create another Admin user.",
    tags=["Admin - Users"] # Tag for Swagger UI grouping
)
async def create_admin_user(
    user_in: UserCreate, # Reuse UserCreate schema for input (email, password, name)
    current_admin: User = Depends(get_current_admin_user) # Enforce admin access
):
    """
    Creates a new user with ADMIN privileges. Requires the requesting user
    to be an authenticated Admin.
    """
    # Check if email already exists
    existing_user = await User.find_one(User.email == user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{user_in.email}' already exists.",
        )

    # Hash the password
    hashed_password = get_password_hash(user_in.password)

    # Create the User document, explicitly setting the type to ADMIN
    admin_user = User(
        email=user_in.email,
        name=user_in.name,
        hashed_password=hashed_password,
        user_type=UserType.ADMIN, # <-- Set user type explicitly
        status=UserStatus.ACTIVE, # Admins are active by default
        is_active=True
        # Add defaults for other fields if needed, or let the model handle them
    )

    # Insert into database
    try:
        inserted_user = await admin_user.insert()
        if not inserted_user or not inserted_user.id:
            raise HTTPException(status_code=500, detail="Failed to create admin user in database.")
    except Exception as e:
        # Catch potential database errors during insert
        print(f"Database error during admin creation: {e}")
        raise HTTPException(status_code=500, detail="Database error creating admin user.")


    # Prepare response data (convert _id)
    user_read_data = {
        "id": str(inserted_user.id),
        "email": inserted_user.email,
        "name": inserted_user.name,
        "avatar_uri": inserted_user.avatar_uri,
        "is_active": inserted_user.is_active,
        "user_type": inserted_user.user_type, # Include user_type
        "created_at": inserted_user.created_at,
        "updated_at": inserted_user.updated_at
    }

    return UserRead(**user_read_data)

# TODO: Add other admin-specific endpoints here later if needed
# (e.g., list users, deactivate users, update user types)