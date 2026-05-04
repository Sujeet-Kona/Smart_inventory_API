from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, ForeignKey, func
from datetime import datetime
from typing import Optional


# All models inherit from this base class
class Base(DeclarativeBase):
    pass


class Item(Base):
    """
    Represents a single product in the inventory.

    Columns:
        id             — Auto-generated primary key
        name           — Product display name
        description    — Optional longer description
        price          — Unit price in USD
        stock_quantity — Units currently in stock
        category       — Product category (see Category enum in schemas.py)
        sku            — Stock Keeping Unit — unique identifier per product
        is_active      — False means the item was soft-deleted
        created_at     — Timestamp set automatically on insert
        updated_at     — Timestamp updated automatically on every change
    """
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Order(Base):
    """
    Records a stock purchase/order event.

    Columns:
        id         — Auto-generated primary key
        item_id    — The item that was ordered (foreign key → items.id)
        quantity   — Number of units ordered
        created_at — Timestamp of the order
    """
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# SQLite for development — easy to run with zero setup.
# To use PostgreSQL in production, change this URL to:
#   postgresql+asyncpg://user:password@localhost/dbname
DATABASE_URL = "sqlite+aiosqlite:///./inventory.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True to print every SQL query (useful for debugging)
    future=True,
)

# Session factory — creates new database sessions
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all database tables. Called once when the app starts."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """
    FastAPI dependency that provides a database session for each request.
    Automatically commits on success, rolls back on error, and always closes.

    Usage in a route:
        db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
