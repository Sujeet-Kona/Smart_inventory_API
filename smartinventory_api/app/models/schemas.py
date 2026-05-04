from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────

class Category(str, Enum):
    """Valid product categories."""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    FOOD = "food"
    BOOKS = "books"
    OTHER = "other"


# ── Request Schemas (what the client sends) ──────────────────────

class ItemCreate(BaseModel):
    """Schema for creating a new inventory item (POST /items)."""
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Optional product description")
    price: float = Field(..., gt=0, description="Price in USD — must be greater than 0")
    stock_quantity: int = Field(..., ge=0, description="Number of units in stock")
    category: Category = Field(..., description="Product category")
    sku: str = Field(..., min_length=3, max_length=50, description="Unique stock keeping unit code")

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str) -> str:
        """SKUs are always stored in uppercase with no surrounding spaces."""
        return v.upper().strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Wireless Bluetooth Headphones",
                "description": "Over-ear noise cancelling headphones",
                "price": 79.99,
                "stock_quantity": 150,
                "category": "electronics",
                "sku": "WBH-2024-BLK",
            }
        }
    }


class ItemUpdate(BaseModel):
    """
    Schema for updating an existing item (PATCH /items/{id}).
    All fields are optional — only include what you want to change.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category: Optional[Category] = None


# ── Response Schemas (what the server returns) ───────────────────

class ItemResponse(BaseModel):
    """Full item data returned in API responses."""
    id: int
    name: str
    description: Optional[str]
    price: float
    stock_quantity: int
    category: Category
    sku: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def is_low_stock(self) -> bool:
        """True when fewer than 5 units remain. Computed on the fly — no DB column needed."""
        return self.stock_quantity < 5

    # from_attributes=True lets Pydantic read from SQLAlchemy ORM objects directly
    model_config = {"from_attributes": True}


class ItemListResponse(BaseModel):
    """Paginated list of items."""
    items: List[ItemResponse]
    total: int       # Total number of matching items (across all pages)
    page: int        # Current page number
    page_size: int   # Number of items per page


# ── Auth Schemas ─────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Returned after a successful login."""
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


# ── Order Schemas ─────────────────────────────────────────────────

class OrderCreate(BaseModel):
    """Schema for placing a new order (POST /orders)."""
    item_id: int = Field(..., ge=1, description="ID of the item to order")
    quantity: int = Field(..., ge=1, description="Number of units to order")

    model_config = {
        "json_schema_extra": {
            "example": {"item_id": 1, "quantity": 3}
        }
    }


class OrderResponse(BaseModel):
    """Order data returned after creation."""
    id: int
    item_id: int
    quantity: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Generic Responses ────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Simple response for operations that don't return data (e.g. delete)."""
    message: str
