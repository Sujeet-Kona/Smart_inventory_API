"""
Tests for authentication endpoints.
Covers: login success/failure, token validation, /me endpoint.
"""
from unittest.mock import patch
from app.utils.auth import create_access_token


# ── Login ─────────────────────────────────────────────────────────

def test_login_with_valid_credentials_returns_token(client):
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "secret123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in_minutes"] > 0


def test_login_with_wrong_password_returns_401(client):
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_with_unknown_user_returns_401(client):
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "nobody", "password": "whatever"},
    )
    assert resp.status_code == 401


# ── /me endpoint ──────────────────────────────────────────────────

def test_get_me_returns_user_info(client):
    """
    The /me endpoint is already authenticated in tests via the
    overridden get_current_user dependency (see conftest.py).
    """
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert "username" in data
    assert "role" in data


# ── JWT validation ────────────────────────────────────────────────

def test_request_without_token_returns_401(client):
    """
    Remove the auth override temporarily to test real JWT validation.
    Without a token, the API should reject the request.
    """
    from app.main import app
    from app.utils.auth import get_current_user

    # Remove the override so real JWT validation kicks in
    app.dependency_overrides.pop(get_current_user, None)

    resp = client.get("/api/v1/items/")
    assert resp.status_code == 401

    # Restore the override so other tests still work
    app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser", "role": "admin"}


def test_request_with_invalid_token_returns_401(client):
    """A tampered or expired token should be rejected."""
    from app.main import app
    from app.utils.auth import get_current_user

    app.dependency_overrides.pop(get_current_user, None)

    resp = client.get(
        "/api/v1/items/",
        headers={"Authorization": "Bearer this.is.not.a.valid.token"},
    )
    assert resp.status_code == 401

    app.dependency_overrides[get_current_user] = lambda: {"sub": "testuser", "role": "admin"}
