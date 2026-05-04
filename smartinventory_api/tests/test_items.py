"""
Tests for inventory item CRUD endpoints.

Covers: create, read, update, delete, stock adjustment,
        pagination, filtering, price range, is_low_stock,
        and input validation edge cases.
"""


# ── Helpers ───────────────────────────────────────────────────────

def create_item(client, payload):
    """Helper to create an item and return the response JSON."""
    resp = client.post("/api/v1/items/", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_payload(base, **overrides):
    """Helper to create a modified copy of a base payload."""
    return {**base, **overrides}


# ── Create ────────────────────────────────────────────────────────

def test_create_item_returns_201(client, sample_item):
    resp = client.post("/api/v1/items/", json=sample_item)
    assert resp.status_code == 201


def test_create_item_response_has_correct_fields(client, sample_item):
    data = create_item(client, sample_item)
    assert data["name"] == sample_item["name"]
    assert data["price"] == sample_item["price"]
    assert data["sku"] == "WBH-TEST-001"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "is_low_stock" in data  # computed field must be present


def test_create_item_sku_is_normalised_to_uppercase(client, sample_item):
    payload = make_payload(sample_item, sku="wbh-lowercase-001")
    data = create_item(client, payload)
    assert data["sku"] == "WBH-LOWERCASE-001"


def test_create_duplicate_sku_returns_409(client, sample_item):
    client.post("/api/v1/items/", json=sample_item)
    resp = client.post("/api/v1/items/", json=sample_item)
    assert resp.status_code == 409
    assert "WBH-TEST-001" in resp.json()["detail"]


def test_create_item_with_negative_price_returns_422(client, sample_item):
    resp = client.post("/api/v1/items/", json=make_payload(sample_item, price=-5.00, sku="SKU-NEG-001"))
    assert resp.status_code == 422


def test_create_item_with_negative_stock_returns_422(client, sample_item):
    resp = client.post("/api/v1/items/", json=make_payload(sample_item, stock_quantity=-1, sku="SKU-NEG-002"))
    assert resp.status_code == 422


def test_create_item_with_missing_required_fields_returns_422(client):
    resp = client.post("/api/v1/items/", json={"name": "Incomplete Item"})
    assert resp.status_code == 422


def test_create_item_with_invalid_category_returns_422(client, sample_item):
    resp = client.post("/api/v1/items/", json=make_payload(sample_item, category="invalid_cat"))
    assert resp.status_code == 422


# ── is_low_stock computed field ───────────────────────────────────

def test_is_low_stock_false_when_stock_is_high(client, sample_item):
    """Items with stock >= 5 should have is_low_stock = False."""
    data = create_item(client, make_payload(sample_item, stock_quantity=10))
    assert data["is_low_stock"] is False


def test_is_low_stock_true_when_stock_below_5(client, sample_item):
    """Items with stock < 5 should have is_low_stock = True."""
    data = create_item(client, make_payload(sample_item, stock_quantity=4, sku="SKU-LOW-001"))
    assert data["is_low_stock"] is True


def test_is_low_stock_true_when_stock_is_zero(client, sample_item):
    data = create_item(client, make_payload(sample_item, stock_quantity=0, sku="SKU-ZERO-001"))
    assert data["is_low_stock"] is True


# ── Read by ID ────────────────────────────────────────────────────

def test_get_item_by_id(client, sample_item):
    created = create_item(client, sample_item)
    resp = client.get(f"/api/v1/items/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_nonexistent_item_returns_404(client):
    resp = client.get("/api/v1/items/99999")
    assert resp.status_code == 404


# ── Read by SKU ───────────────────────────────────────────────────

def test_get_item_by_sku(client, sample_item):
    create_item(client, sample_item)
    resp = client.get(f"/api/v1/items/sku/{sample_item['sku']}")
    assert resp.status_code == 200
    assert resp.json()["sku"] == sample_item["sku"].upper()


def test_get_item_by_sku_is_case_insensitive(client, sample_item):
    create_item(client, sample_item)
    resp = client.get(f"/api/v1/items/sku/{sample_item['sku'].lower()}")
    assert resp.status_code == 200


# ── List / Pagination / Filtering ─────────────────────────────────

def test_list_items_returns_200(client, sample_item):
    create_item(client, sample_item)
    resp = client.get("/api/v1/items/")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


def test_list_items_pagination(client, sample_item):
    """Create 3 items and verify page_size=2 returns only 2."""
    for i in range(3):
        create_item(client, make_payload(sample_item, sku=f"SKU-PAGE-{i}"))
    resp = client.get("/api/v1/items/?page=1&page_size=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3


def test_list_items_filter_by_category(client, sample_item):
    create_item(client, sample_item)
    create_item(client, make_payload(sample_item, category="books", sku="SKU-BOOK-001"))
    resp = client.get("/api/v1/items/?category=electronics")
    data = resp.json()
    assert all(i["category"] == "electronics" for i in data["items"])


def test_list_items_search_by_name(client, sample_item):
    create_item(client, sample_item)
    create_item(client, make_payload(sample_item, name="Mechanical Keyboard", sku="SKU-KB-001"))
    resp = client.get("/api/v1/items/?search=keyboard")
    data = resp.json()
    assert len(data["items"]) == 1
    assert "Keyboard" in data["items"][0]["name"]


def test_list_items_filter_by_price_range(client, sample_item):
    """Only items within the given price range should be returned."""
    create_item(client, make_payload(sample_item, price=10.00, sku="SKU-CHEAP"))
    create_item(client, make_payload(sample_item, price=200.00, sku="SKU-EXPENSIVE"))

    resp = client.get("/api/v1/items/?min_price=50&max_price=150")
    data = resp.json()
    # 79.99 (sample_item default) falls in range, 10 and 200 do not
    for item in data["items"]:
        assert 50 <= item["price"] <= 150


def test_list_items_in_stock_only(client, sample_item):
    create_item(client, sample_item)
    create_item(client, make_payload(sample_item, stock_quantity=0, sku="SKU-EMPTY-001"))
    resp = client.get("/api/v1/items/?in_stock_only=true")
    data = resp.json()
    assert all(i["stock_quantity"] > 0 for i in data["items"])


# ── Update ────────────────────────────────────────────────────────

def test_update_item_price(client, sample_item):
    created = create_item(client, sample_item)
    resp = client.patch(f"/api/v1/items/{created['id']}", json={"price": 49.99})
    assert resp.status_code == 200
    assert resp.json()["price"] == 49.99


def test_update_nonexistent_item_returns_404(client):
    resp = client.patch("/api/v1/items/99999", json={"price": 10.00})
    assert resp.status_code == 404


def test_update_with_invalid_price_returns_422(client, sample_item):
    created = create_item(client, sample_item)
    resp = client.patch(f"/api/v1/items/{created['id']}", json={"price": -1})
    assert resp.status_code == 422


# ── Stock Adjustment ──────────────────────────────────────────────

def test_adjust_stock_add_units(client, sample_item):
    created = create_item(client, sample_item)
    resp = client.post(f"/api/v1/items/{created['id']}/stock?delta=50")
    assert resp.status_code == 200
    assert resp.json()["stock_quantity"] == sample_item["stock_quantity"] + 50


def test_adjust_stock_remove_units(client, sample_item):
    created = create_item(client, sample_item)
    resp = client.post(f"/api/v1/items/{created['id']}/stock?delta=-10")
    assert resp.status_code == 200
    assert resp.json()["stock_quantity"] == sample_item["stock_quantity"] - 10


def test_adjust_stock_below_zero_returns_400(client, sample_item):
    created = create_item(client, sample_item)
    resp = client.post(f"/api/v1/items/{created['id']}/stock?delta=-99999")
    assert resp.status_code == 400


# ── Delete (soft) ─────────────────────────────────────────────────

def test_delete_item_returns_200(client, sample_item):
    created = create_item(client, sample_item)
    resp = client.delete(f"/api/v1/items/{created['id']}")
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"]


def test_deleted_item_not_returned_in_list(client, sample_item):
    created = create_item(client, sample_item)
    client.delete(f"/api/v1/items/{created['id']}")
    resp = client.get("/api/v1/items/")
    ids = [i["id"] for i in resp.json()["items"]]
    assert created["id"] not in ids


def test_deleted_item_not_returned_by_id(client, sample_item):
    created = create_item(client, sample_item)
    client.delete(f"/api/v1/items/{created['id']}")
    resp = client.get(f"/api/v1/items/{created['id']}")
    assert resp.status_code == 404
