# SmartInventory API

A REST API for managing product inventory built with FastAPI and SQLite. Demonstrates core backend fundamentals: JWT authentication, role-based access control, clean service-layer architecture, input validation, and automated tests.

---

## Features

- **JWT Authentication** — Login to get a token; include it in every request
- **Role-Based Access Control** — Admins can write; viewers can only read
- **CRUD for Inventory Items** — Create, read, update, and soft-delete products
- **Orders** — Place an order; stock is validated and deducted automatically
- **Pagination & Filtering** — Filter by category, name, price range, or stock status
- **Low-Stock Flag** — `is_low_stock` is computed on the fly (no extra DB column)
- **Input Validation** — Invalid requests get a clear `422` error with field-level detail
- **Soft Deletes** — Items are marked inactive, not permanently removed

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Framework  | FastAPI                           |
| Database   | SQLite via SQLAlchemy (async ORM) |
| Auth       | JWT (HS256) + bcrypt              |
| Validation | Pydantic v2                       |
| Testing    | pytest + FastAPI TestClient       |
| Deployment | Docker / Docker Compose           |

---

## Project Structure

```
smartinventory_api/
├── app/
│   ├── api/
│   │   ├── dependencies.py      # Shared deps: get_current_user, require_admin
│   │   └── v1/
│   │       ├── auth.py          # POST /auth/token, GET /auth/me
│   │       ├── items.py         # Full CRUD for inventory items
│   │       ├── orders.py        # POST /orders
│   │       └── health.py        # GET /health
│   ├── models/
│   │   ├── database.py          # SQLAlchemy models (Item, Order) + DB session
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── services/
│   │   ├── item_service.py      # Item business logic (DB operations)
│   │   └── order_service.py     # Order creation + stock deduction
│   ├── utils/
│   │   ├── auth.py              # JWT creation and verification
│   │   └── logger.py            # Application logger
│   ├── config.py                # Settings loaded from .env
│   └── main.py                  # App factory, middleware, error handlers
├── tests/
│   ├── conftest.py              # Shared fixtures (admin client, viewer client)
│   ├── test_auth.py             # Login, token validation
│   ├── test_items.py            # Item CRUD, filtering, edge cases
│   ├── test_orders.py           # Order creation, stock deduction
│   └── test_rbac.py             # Role-based access control
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Running Locally

### Without Docker

**Requirements:** Python 3.11+

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd smartinventory_api

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env — set a strong JWT_SECRET_KEY

# 5. Start the server
uvicorn app.main:app --reload
```

Visit **http://localhost:8000/docs** for the interactive Swagger UI.

### With Docker

```bash
docker-compose up --build
```

---

## Authentication

All endpoints require a JWT token. Get one by logging in:

```bash
# Step 1 — Log in
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=secret123"

# Step 2 — Use the token
curl http://localhost:8000/api/v1/items/ \
  -H "Authorization: Bearer <your_token>"
```

**Demo accounts:**

| Username | Password  | Role   | Can do                    |
|----------|-----------|--------|---------------------------|
| admin    | secret123 | admin  | Read + Write (full access)|
| viewer   | viewer123 | viewer | Read only                 |

> Credentials are hardcoded for simplicity. In production, users would be stored in the database.

---

## API Endpoints

### Authentication

| Method | Endpoint              | Description                  |
|--------|-----------------------|------------------------------|
| POST   | `/api/v1/auth/token`  | Log in and get a JWT token   |
| GET    | `/api/v1/auth/me`     | Get current user info        |

### Inventory Items

| Method | Endpoint                    | Role   | Description                     |
|--------|-----------------------------|--------|---------------------------------|
| GET    | `/api/v1/items/`            | Any    | List items (paginated, filtered)|
| GET    | `/api/v1/items/{id}`        | Any    | Get item by ID                  |
| GET    | `/api/v1/items/sku/{sku}`   | Any    | Get item by SKU                 |
| POST   | `/api/v1/items/`            | Admin  | Create a new item               |
| PATCH  | `/api/v1/items/{id}`        | Admin  | Partially update an item        |
| POST   | `/api/v1/items/{id}/stock`  | Admin  | Adjust stock quantity           |
| DELETE | `/api/v1/items/{id}`        | Admin  | Soft-delete an item             |

### Orders

| Method | Endpoint        | Role  | Description                                   |
|--------|-----------------|-------|-----------------------------------------------|
| POST   | `/api/v1/orders/` | Admin | Place an order (validates + deducts stock)  |

### Query Parameters for `GET /items/`

| Parameter      | Type   | Description                           |
|----------------|--------|---------------------------------------|
| `page`         | int    | Page number (default: 1)              |
| `page_size`    | int    | Items per page, max 100 (default: 20) |
| `category`     | string | Filter by category                    |
| `search`       | string | Search by name (partial match)        |
| `in_stock_only`| bool   | Only items with stock > 0             |
| `min_price`    | float  | Minimum price filter                  |
| `max_price`    | float  | Maximum price filter                  |

---

## Running Tests

```bash
pytest           # Run all tests
pytest -v        # Verbose output (see each test name)
pytest tests/test_rbac.py  # Run a specific file
```

Tests use an **in-memory SQLite database** and bypass JWT verification — no setup needed.

---

## Key Design Decisions

**Service Layer** — Business logic lives in `ItemService` and `OrderService`, not in routes. Routes handle HTTP concerns only (parsing input, returning responses). This separation makes each layer easier to test and change independently.

**Role-Based Access Control** — A single `require_admin` dependency is added to any route that needs it. The role comes from the JWT payload, so there's no extra database lookup per request.

**`is_low_stock` as a Computed Field** — Rather than storing a boolean in the database (which would go stale), `is_low_stock` is derived from `stock_quantity < 5` at response time using Pydantic's `@computed_field`. No schema migration needed if the threshold changes.

**Soft Deletes** — Items are marked `is_active=False` instead of being permanently removed. This preserves data for auditing and prevents accidental data loss.

**Pydantic Validation** — All request data is validated before reaching the service layer. Invalid input returns a `422` with clear field-level error messages.

---

## Environment Variables

| Variable             | Default   | Description                    |
|----------------------|-----------|--------------------------------|
| `JWT_SECRET_KEY`     | *(set this!)* | Secret used to sign JWT tokens |
| `JWT_ALGORITHM`      | `HS256`   | JWT signing algorithm          |
| `JWT_EXPIRE_MINUTES` | `30`      | Token lifetime in minutes      |
| `DEBUG`              | `false`   | Enable debug logging           |

Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
