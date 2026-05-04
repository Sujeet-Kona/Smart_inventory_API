from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models.database import get_db
from app.models.schemas import (
    ItemCreate, ItemUpdate, ItemResponse, ItemListResponse,
    MessageResponse, Category,
)
from app.services.item_service import ItemService
from app.utils.auth import get_current_user
from app.api.dependencies import require_admin

router = APIRouter(prefix="/items", tags=["Inventory Items"])


@router.get(
    "/",
    response_model=ItemListResponse,
    summary="List items with pagination and optional filters",
)
async def list_items(
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    category: Optional[Category] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, min_length=1, description="Search items by name"),
    in_stock_only: bool = Query(False, description="Only return items with stock > 0"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a paginated list of active inventory items.
    Supports filtering by category, name search, stock status, and price range.
    """
    service = ItemService(db)
    items, total = await service.list_items(
        page=page,
        page_size=page_size,
        category=category,
        search=search,
        in_stock_only=in_stock_only,
        min_price=min_price,
        max_price=max_price,
    )
    return ItemListResponse(
        items=[ItemResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new inventory item (admin only)",
)
async def create_item(
    payload: ItemCreate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new product to the inventory. Requires admin role.
    The SKU must be unique — a 409 error is returned if it already exists.
    """
    service = ItemService(db)
    item = await service.create(payload)
    return ItemResponse.model_validate(item)


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Get a single item by ID",
)
async def get_item(
    item_id: int = Path(..., ge=1, description="The item's ID"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single inventory item by its numeric ID."""
    service = ItemService(db)
    item = await service.get_by_id(item_id)
    return ItemResponse.model_validate(item)


@router.get(
    "/sku/{sku}",
    response_model=ItemResponse,
    summary="Get a single item by SKU",
)
async def get_item_by_sku(
    sku: str = Path(..., min_length=3, description="The item's SKU code"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single inventory item by its SKU. The lookup is case-insensitive."""
    service = ItemService(db)
    item = await service.get_by_sku(sku)
    return ItemResponse.model_validate(item)


@router.patch(
    "/{item_id}",
    response_model=ItemResponse,
    summary="Partially update an item (admin only)",
)
async def update_item(
    payload: ItemUpdate,
    item_id: int = Path(..., ge=1),
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update one or more fields on an existing item. Requires admin role.
    Only include the fields you want to change in the request body.
    """
    service = ItemService(db)
    item = await service.update(item_id, payload)
    return ItemResponse.model_validate(item)


@router.post(
    "/{item_id}/stock",
    response_model=ItemResponse,
    summary="Adjust stock quantity (admin only)",
)
async def adjust_stock(
    item_id: int = Path(..., ge=1),
    delta: int = Query(..., description="Units to add (positive) or remove (negative)"),
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Adjust stock by adding or subtracting units. Requires admin role.

    - delta=50  → adds 50 units (restocking)
    - delta=-10 → removes 10 units (sale or write-off)

    Returns 400 if the adjustment would result in negative stock.
    """
    service = ItemService(db)
    item = await service.adjust_stock(item_id, delta)
    return ItemResponse.model_validate(item)


@router.delete(
    "/{item_id}",
    response_model=MessageResponse,
    summary="Delete an item (admin only)",
)
async def delete_item(
    item_id: int = Path(..., ge=1),
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft-delete an item — marks it as inactive without removing the database row.
    This preserves history for auditing. The item will no longer appear in any API responses.
    """
    service = ItemService(db)
    await service.soft_delete(item_id)
    return MessageResponse(message=f"Item {item_id} has been deleted.")
