# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.models.user import User
from app.schemas.user import UserRead, UserUpdate # Import UserUpdate if adding update endpoint
from app.api.deps import get_current_active_user

router = APIRouter()

@router.get("/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current logged-in user's details.
    """
    user_dict = current_user.model_dump() # Use model_dump without alias initially
    user_read_data = {
        "id": str(user_dict['_id']), # Convert ObjectId to string for 'id' field
        "email": user_dict['email'],
        "name": user_dict['name'],
        "avatar_uri": user_dict.get('avatar_uri'),
        "is_active": user_dict.get('is_active', True), # Handle potential missing value
        "user_type": user_dict['user_type'], # Include user_type (ensure it's in UserRead schema)
        "created_at": user_dict['created_at'],
        "updated_at": user_dict['updated_at']
    }
    # ---------------------------------------------

    # Pass the prepared dictionary to the response model
    return UserRead(**user_read_data)

# --- OPTIONAL: Add Update Endpoint ---
# @router.patch("/me", response_model=UserRead)
# async def update_user_me(
#     user_in: UserUpdate,
#     current_user: User = Depends(get_current_active_user)
# ):
#     """
#     Update current user's profile (name, email, avatar).
#     """
#     update_data = user_in.model_dump(exclude_unset=True) # Get only fields that were set
#     if not update_data:
#          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

#     # Prevent changing email if needed, or add verification logic
#     if "email" in update_data and update_data["email"] != current_user.email:
#         existing_user = await User.find_one(User.email == update_data["email"])
#         if existing_user:
#              raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

#     # Update user object
#     for field, value in update_data.items():
#         setattr(current_user, field, value)

#     await current_user.save()
#     return UserRead(**current_user.model_dump(by_alias=True))