"""
Tests for the orders endpoint.

Covers: successful order creation, stock deduction,
        insufficient stock, and invalid item ID.
"""


def create_item(client, payload):
    resp = client.post("/api/v1/items/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Successful order ──────────────────────────────────────────────

def test_create_order_returns_201(client, sample_item):
    item = create_item(client, sample_item)
    resp = client.post("/api/v1/orders/", json={"item_id": item["id"], "quantity": 5})
    assert resp.status_code == 201
    data = resp.json()
    assert data["item_id"] == item["id"]
    assert data["quantity"] == 5
    assert "id" in data
    assert "created_at" in data


def test_order_reduces_stock(client, sample_item):
    """After an order, the item's stock_quantity should decrease."""
    item = create_item(client, sample_item)
    original_stock = item["stock_quantity"]

    client.post("/api/v1/orders/", json={"item_id": item["id"], "quantity": 10})

    updated = client.get(f"/api/v1/items/{item['id']}").json()
    assert updated["stock_quantity"] == original_stock - 10


# ── Edge cases ────────────────────────────────────────────────────

def test_order_with_exact_stock_succeeds(client, sample_item):
    """Ordering exactly the available quantity should succeed."""
    item = create_item(client, sample_item)
    resp = client.post(
        "/api/v1/orders/",
        json={"item_id": item["id"], "quantity": item["stock_quantity"]},
    )
    assert resp.status_code == 201

    # Stock should now be zero
    updated = client.get(f"/api/v1/items/{item['id']}").json()
    assert updated["stock_quantity"] == 0


def test_order_exceeding_stock_returns_400(client, sample_item):
    """Ordering more than available stock should be rejected."""
    item = create_item(client, sample_item)
    resp = client.post(
        "/api/v1/orders/",
        json={"item_id": item["id"], "quantity": item["stock_quantity"] + 1},
    )
    assert resp.status_code == 400
    assert "Not enough stock" in resp.json()["detail"]


def test_order_for_nonexistent_item_returns_404(client):
    resp = client.post("/api/v1/orders/", json={"item_id": 99999, "quantity": 1})
    assert resp.status_code == 404


def test_order_with_zero_quantity_returns_422(client, sample_item):
    """Quantity must be at least 1."""
    item = create_item(client, sample_item)
    resp = client.post("/api/v1/orders/", json={"item_id": item["id"], "quantity": 0})
    assert resp.status_code == 422
