"""
Tests for Role-Based Access Control (RBAC).

Verifies that:
- Viewers can access read (GET) endpoints.
- Viewers are blocked from write (POST, PATCH, DELETE) endpoints.
- Unauthenticated requests are rejected.
"""
from app.main import app
from app.utils.auth import get_current_user


def create_item_as_admin(client, payload):
    """Helper: creates an item using the admin client."""
    resp = client.post("/api/v1/items/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Viewer can read ───────────────────────────────────────────────

def test_viewer_can_list_items(viewer_client):
    resp = viewer_client.get("/api/v1/items/")
    assert resp.status_code == 200


def test_viewer_can_get_item_by_id(client, viewer_client, sample_item):
    # Admin creates an item first
    created = create_item_as_admin(client, sample_item)
    resp = viewer_client.get(f"/api/v1/items/{created['id']}")
    assert resp.status_code == 200


# ── Viewer is blocked from writes ─────────────────────────────────

def test_viewer_cannot_create_item(viewer_client, sample_item):
    resp = viewer_client.post("/api/v1/items/", json=sample_item)
    assert resp.status_code == 403
    assert "Admin access required" in resp.json()["detail"]


def test_viewer_cannot_update_item(client, viewer_client, sample_item):
    created = create_item_as_admin(client, sample_item)
    resp = viewer_client.patch(f"/api/v1/items/{created['id']}", json={"price": 9.99})
    assert resp.status_code == 403


def test_viewer_cannot_delete_item(client, viewer_client, sample_item):
    created = create_item_as_admin(client, sample_item)
    resp = viewer_client.delete(f"/api/v1/items/{created['id']}")
    assert resp.status_code == 403


def test_viewer_cannot_place_order(viewer_client, sample_item):
    resp = viewer_client.post("/api/v1/orders/", json={"item_id": 1, "quantity": 1})
    assert resp.status_code == 403


# ── Unauthenticated requests ──────────────────────────────────────

def test_no_token_returns_401(client):
    """Remove the auth override so real JWT validation runs."""
    app.dependency_overrides.pop(get_current_user, None)

    resp = client.get("/api/v1/items/")
    assert resp.status_code == 401

    # Restore for other tests
    from tests.conftest import make_user
    app.dependency_overrides[get_current_user] = lambda: make_user("admin")


def test_invalid_token_returns_401(client):
    app.dependency_overrides.pop(get_current_user, None)

    resp = client.get(
        "/api/v1/items/",
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert resp.status_code == 401

    from tests.conftest import make_user
    app.dependency_overrides[get_current_user] = lambda: make_user("admin")
