from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.models.schemas import TokenResponse
from app.utils.auth import authenticate_user, create_access_token, get_current_user
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Log in and get a JWT token",
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Exchange a username and password for a JWT access token.

    Demo credentials:
    - admin / secret123  (full access)
    - viewer / viewer123 (read-only)

    Use the returned token in subsequent requests:
        Authorization: Bearer <token>
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    settings = get_settings()

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.jwt_expire_minutes,
    )


@router.get(
    "/me",
    summary="Get current user info",
)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Returns information about the currently logged-in user.
    Requires a valid JWT token in the Authorization header.
    """
    return {
        "username": current_user.get("sub"),
        "role": current_user.get("role"),
    }
