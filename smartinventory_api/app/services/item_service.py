from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List, Tuple
from fastapi import HTTPException, status

from app.models.database import Item
from app.models.schemas import ItemCreate, ItemUpdate, Category
from app.utils.logger import get_logger

logger = get_logger("item_service")


class ItemService:
    """
    Handles all database operations for inventory items.

    This layer sits between the API routes and the database:
      Routes  →  ItemService  →  Database

    Keeping business logic here (instead of in routes) makes the
    code easier to test and maintain.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: ItemCreate) -> Item:
        """
        Add a new item to the inventory.
        Raises HTTP 409 if an item with the same SKU already exists.
        """
        # Check for duplicate SKU before inserting
        existing = await self.db.execute(
            select(Item).where(Item.sku == payload.sku)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An item with SKU '{payload.sku}' already exists.",
            )

        item = Item(
            name=payload.name,
            description=payload.description,
            price=payload.price,
            stock_quantity=payload.stock_quantity,
            category=payload.category.value,
            sku=payload.sku,
            is_active=True,
        )
        self.db.add(item)
        await self.db.flush()       # Send INSERT to DB and get the generated ID
        await self.db.refresh(item) # Load the full row back (including timestamps)

        logger.info(f"Item created — id={item.id}, sku={item.sku}")
        return item

    async def get_by_id(self, item_id: int) -> Item:
        """
        Fetch a single active item by its ID.
        Raises HTTP 404 if the item doesn't exist or was deleted.
        """
        result = await self.db.execute(
            select(Item).where(Item.id == item_id, Item.is_active == True)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id={item_id} not found.",
            )
        return item

    async def get_by_sku(self, sku: str) -> Item:
        """
        Fetch a single active item by its SKU.
        SKU comparison is case-insensitive (normalised to uppercase).
        """
        result = await self.db.execute(
            select(Item).where(Item.sku == sku.upper(), Item.is_active == True)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with SKU='{sku.upper()}' not found.",
            )
        return item

    async def list_items(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[Category] = None,
        search: Optional[str] = None,
        in_stock_only: bool = False,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> Tuple[List[Item], int]:
        """
        Return a paginated list of active items with optional filters.
        Returns a tuple of (items_on_this_page, total_matching_count).
        """
        # Start with a base query — only active items
        query = select(Item).where(Item.is_active == True)

        # Apply optional filters
        if category:
            query = query.where(Item.category == category.value)
        if search:
            query = query.where(Item.name.ilike(f"%{search}%"))
        if in_stock_only:
            query = query.where(Item.stock_quantity > 0)
        if min_price is not None:
            query = query.where(Item.price >= min_price)
        if max_price is not None:
            query = query.where(Item.price <= max_price)

        # Count total matching rows (for pagination metadata)
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Fetch the requested page
        offset = (page - 1) * page_size
        result = await self.db.execute(
            query.order_by(Item.created_at.desc()).offset(offset).limit(page_size)
        )
        items = list(result.scalars().all())

        return items, total

    async def update(self, item_id: int, payload: ItemUpdate) -> Item:
        """
        Partially update an item — only fields included in payload are changed.
        Raises HTTP 404 if the item doesn't exist.
        """
        item = await self.get_by_id(item_id)

        # model_dump(exclude_unset=True) only returns fields the client actually sent
        update_data = payload.model_dump(exclude_unset=True)

        if not update_data:
            return item  # Nothing to update

        # Convert enum values to strings for storage
        if "category" in update_data and update_data["category"]:
            update_data["category"] = update_data["category"].value

        for field, value in update_data.items():
            setattr(item, field, value)

        await self.db.flush()
        await self.db.refresh(item)
        logger.info(f"Item updated — id={item_id}, fields={list(update_data.keys())}")
        return item

    async def soft_delete(self, item_id: int) -> None:
        """
        Mark an item as inactive instead of deleting it from the database.

        Why soft delete? It preserves the data for auditing and reporting,
        and prevents accidentally losing important records.
        The item will no longer appear in any list or GET responses.
        """
        item = await self.get_by_id(item_id)
        item.is_active = False
        await self.db.flush()
        logger.info(f"Item soft-deleted — id={item_id}")

    async def adjust_stock(self, item_id: int, delta: int) -> Item:
        """
        Change the stock quantity by a given amount.
        Use a positive delta to add stock, negative to reduce it.
        Raises HTTP 400 if the adjustment would result in negative stock.
        """
        item = await self.get_by_id(item_id)
        new_quantity = item.stock_quantity + delta

        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot set stock to a negative value. "
                    f"Current stock: {item.stock_quantity}, requested change: {delta}."
                ),
            )

        item.stock_quantity = new_quantity
        await self.db.flush()
        await self.db.refresh(item)
        logger.info(f"Stock adjusted — id={item_id}, delta={delta}, new_quantity={new_quantity}")
        return item
