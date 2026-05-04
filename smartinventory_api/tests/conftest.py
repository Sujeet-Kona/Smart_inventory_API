"""
Shared test fixtures used across all test files.
pytest automatically loads this file before running any tests.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.models.database import Base, get_db
from app.utils.auth import get_current_user
from app.api.dependencies import require_admin

# In-memory SQLite database for tests — no files, no cleanup needed
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    """Replaces the real database session with a test one."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def make_user(role: str = "admin"):
    """Returns a fake user dict for the given role."""
    return {"sub": f"test_{role}", "role": role}


@pytest.fixture(scope="function")
def client():
    """
    Test client authenticated as admin.
    Each test gets a fresh in-memory database.
    """
    import asyncio

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: make_user("admin")
    app.dependency_overrides[require_admin] = lambda: make_user("admin")

    asyncio.get_event_loop().run_until_complete(_reset_tables())

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def viewer_client():
    """
    Test client authenticated as a viewer (read-only role).
    Used to test that write endpoints are correctly restricted.
    """
    import asyncio

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: make_user("viewer")
    # require_admin is NOT overridden — real RBAC check runs

    asyncio.get_event_loop().run_until_complete(_reset_tables())

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


async def _reset_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def sample_item():
    """A valid item payload reused across multiple tests."""
    return {
        "name": "Wireless Bluetooth Headphones",
        "description": "Over-ear noise cancelling",
        "price": 79.99,
        "stock_quantity": 100,
        "category": "electronics",
        "sku": "WBH-TEST-001",
    }
