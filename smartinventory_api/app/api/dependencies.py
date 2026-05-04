from fastapi import Depends, HTTPException, status
from app.utils.auth import get_current_user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency that restricts access to admin users only.
    Raises HTTP 403 if the logged-in user is not an admin.

    Usage in a route:
        current_user: dict = Depends(require_admin)
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user
