# app/api/deps.py
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
# Import both schemes
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from beanie.exceptions import DocumentNotFound
import traceback

from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.models.enums import UserType
from app.schemas.token import TokenData

# Keep the OAuth2 scheme for INTERNAL token extraction logic
oauth2_scheme_internal = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    auto_error=False # Set auto_error=False to handle token extraction manually below
)

# Define the HTTPBearer scheme primarily for DOCUMENTATION purposes
bearer_scheme_docs = HTTPBearer(
    scheme_name="APITokenAuth", # Give it a distinct name for Swagger UI
    description="Enter JWT token prefixed with 'Bearer '",
    auto_error=False # Also set to false, we'll handle errors manually
)

async def get_current_user(
    # Use BOTH dependencies, but prioritize HTTPBearer for the actual token value
    # This forces Swagger UI to use the HTTPBearer input, but we can still try the OAuth2 one as fallback
    request: Request,
    auth_header_creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme_docs),
    token_from_oauth2: Optional[str] = Depends(oauth2_scheme_internal)
) -> User:

    print("\n--- Inside get_current_user dependency ---")
    raw_auth_header = request.headers.get("Authorization")
    print(f"Raw Authorization Header: {raw_auth_header}")
    print(f"Token extracted by HTTPBearer: {auth_header_creds.credentials[:15] + '...' if auth_header_creds else 'None'}")
    print(f"Token extracted by OAuth2PasswordBearer: {token_from_oauth2[:15] + '...' if token_from_oauth2 else 'None'}")

    token: Optional[str] = None
    if auth_header_creds and auth_header_creds.scheme.lower() == 'bearer':
        token = auth_header_creds.credentials
        print("Using token from HTTPBearer credentials.")
    elif token_from_oauth2:
         # Fallback: Sometimes OAuth2PasswordBearer might still work even if HTTPBearer failed UI-wise
         print("WARNING: Using token from OAuth2PasswordBearer as HTTPBearer failed or was empty.")
         token = token_from_oauth2
    # If still no token after checking both...
    if token is None:
        print("Authorization token could not be extracted by either scheme.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (token missing or invalid)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- Rest of the function remains the same ---
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    email = decode_access_token(token) # decode_access_token already has logging
    if email is None:
        print("get_current_user: decode_access_token returned None.")
        raise credentials_exception
    token_data = TokenData(email=email)
    print(f"get_current_user: Token data created for email: {token_data.email}")
    try:
        print(f"get_current_user: Attempting DB lookup for email: {token_data.email}")
        user = await User.find_one(User.email == token_data.email)
        if user is None:
            print(f"get_current_user: User not found in DB for email: {token_data.email}")
            raise credentials_exception
        print(f"get_current_user: User found: {user.email}, Active: {user.is_active}")
        return user
    except Exception as e:
        print(f"get_current_user: Unexpected error during DB lookup: {e}")
        print(traceback.format_exc())
        raise credentials_exception

# --- get_current_active_user and get_current_admin_user remain unchanged ---
# They depend on the result of the modified get_current_user above
async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    # ... (no changes needed) ...
    print(f"--- Inside get_current_active_user for {current_user.email} ---")
    if not current_user.is_active: print(f"User {current_user.email} is inactive."); raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    print(f"User {current_user.email} is active.")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
     # ... (no changes needed) ...
    print(f"--- Inside get_current_admin_user for {current_user.email} ---")
    if current_user.user_type != UserType.ADMIN: print(f"User {current_user.email} is not ADMIN (type: {current_user.user_type}). Access denied."); raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation not permitted: Requires admin privileges.")
    print(f"User {current_user.email} is ADMIN. Access granted.")
    return current_user