from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.database import Item, Order
from app.models.schemas import OrderCreate
from app.utils.logger import get_logger

logger = get_logger("order_service")


class OrderService:
    """
    Handles order creation and stock validation.

    When an order is placed:
      1. Verify the item exists and has enough stock.
      2. Deduct the ordered quantity from stock.
      3. Save the order record.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order(self, payload: OrderCreate) -> Order:
        """
        Place an order for an item.
        Raises HTTP 404 if the item doesn't exist.
        Raises HTTP 400 if there's not enough stock.
        """
        # Fetch the item
        result = await self.db.execute(
            select(Item).where(Item.id == payload.item_id, Item.is_active == True)
        )
        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with id={payload.item_id} not found.",
            )

        if item.stock_quantity < payload.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Not enough stock. "
                    f"Requested: {payload.quantity}, available: {item.stock_quantity}."
                ),
            )

        # Deduct stock
        item.stock_quantity -= payload.quantity

        # Record the order
        order = Order(item_id=payload.item_id, quantity=payload.quantity)
        self.db.add(order)

        await self.db.flush()
        await self.db.refresh(order)

        logger.info(f"Order created — id={order.id}, item_id={payload.item_id}, qty={payload.quantity}")
        return order
