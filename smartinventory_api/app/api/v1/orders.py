from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import OrderCreate, OrderResponse
from app.services.order_service import OrderService
from app.api.dependencies import require_admin

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order for an item",
)
async def create_order(
    payload: OrderCreate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Place an order for an item. Validates stock and deducts the quantity automatically.
    Returns HTTP 400 if there isn't enough stock to fulfil the order.
    """
    service = OrderService(db)
    order = await service.create_order(payload)
    return OrderResponse.model_validate(order)
