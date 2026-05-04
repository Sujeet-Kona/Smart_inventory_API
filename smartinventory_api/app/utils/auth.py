from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from app.config import get_settings

# OAuth2 scheme tells FastAPI where clients get tokens from
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# Demo users — in a real app these would be stored in the database
# Passwords are bcrypt-hashed (never store plain text passwords)
DEMO_USERS = {
    "admin": {
        "username": "admin",
        # Hash of "secret123" — generated with: bcrypt.hashpw(b"secret123", bcrypt.gensalt())
        "hashed_password": "$2b$12$YqKDV5vyN3z2RrlNKSeYFO1f6jZgpCwpZEdOLQdeoDtwyyZmIi.w2",
        "role": "admin",
    },
    "viewer": {
        "username": "viewer",
        # Hash of "viewer123"
        "hashed_password": "$2b$12$bMc1kX8bWsRFV8AZOKD/.ezBgFTPI7txIXLnQ4uiRgQPwcYD5EQV6",
        "role": "viewer",
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plain text password matches the stored bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def authenticate_user(username: str, password: str) -> dict | None:
    """
    Look up the user and verify their password.
    Returns the user dict on success, None if credentials are wrong.
    """
    user = DEMO_USERS.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict) -> str:
    """
    Create a signed JWT token.
    The token encodes the user's identity and expires after a set time.
    Anyone with the secret key can verify the token is legitimate.
    """
    settings = get_settings()
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency: validates the JWT token from the Authorization header.
    Raises HTTP 401 if the token is missing, expired, or tampered with.

    Usage in a route:
        current_user: dict = Depends(get_current_user)
    """
    settings = get_settings()

    try:
        # Decode and verify the token signature
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if not username:
            raise ValueError("Token missing subject")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload
