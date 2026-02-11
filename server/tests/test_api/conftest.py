"""
API 测试配置

提供测试 fixtures 和测试工具函数。
"""

import pytest
import pytest_asyncio
import os
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from main import app
from src.core.settings import settings
from src.api.deps import get_current_user
from src.models.user import User


def _get_test_async_db_url() -> str:
    db_url = (
        os.getenv("TEST_DATABASE_URL_ASYNC")
        or os.getenv("DATABASE_URL_ASYNC")
        or settings.database_url
    )
    if not db_url:
        raise RuntimeError("Missing test database URL. Set TEST_DATABASE_URL_ASYNC.")
    if "sqlite" in db_url.lower():
        raise RuntimeError(
            f"SQLite is not allowed for tests. Got: {db_url}. "
            "Use PostgreSQL URL via TEST_DATABASE_URL_ASYNC."
        )
    return db_url


# 配置 pytest-asyncio
@pytest.fixture(autouse=True)
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """
    创建测试客户端

    使用 httpx.AsyncClient 测试 FastAPI 应用。
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
def api_auth_override():
    """Keep production auth dependencies intact; override only for API tests."""
    fastapi_app = app.app if hasattr(app, "app") else app

    async def _mock_current_user():
        return User(
            email="api-test@example.com",
            password_hash="test-hash",
            username="api_test_user",
            is_active=True,
            is_verified=True,
            role="admin",
            permissions=["read", "write", "admin"],
        )

    fastapi_app.dependency_overrides[get_current_user] = _mock_current_user
    yield
    fastapi_app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def test_session():
    """
    创建测试数据库会话

    使用 PostgreSQL 测试数据库进行测试。
    """
    db_url = _get_test_async_db_url()
    schema = f"test_{uuid.uuid4().hex[:12]}"

    admin_engine = create_async_engine(db_url, echo=False)
    async with admin_engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    await admin_engine.dispose()

    engine = create_async_engine(
        db_url,
        echo=False,
        connect_args={"server_settings": {"search_path": schema}},
    )

    # 创建所有表
    from src.models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 创建会话
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()

    cleanup_engine = create_async_engine(db_url, echo=False)
    async with cleanup_engine.begin() as conn:
        await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    await cleanup_engine.dispose()


# 测试数据 fixtures
@pytest.fixture
def sample_sector_data():
    """示例板块数据"""
    return [
        {
            "code": "BK0001",
            "name": "人工智能",
            "type": "concept",
            "description": "人工智能相关概念板块",
            "strength_score": 78.5,
            "trend_direction": 1,
        },
        {
            "code": "BK0002",
            "name": "新能源汽车",
            "type": "concept",
            "description": "新能源汽车相关板块",
            "strength_score": 65.0,
            "trend_direction": 1,
        },
    ]


@pytest.fixture
def sample_stock_data():
    """示例个股数据"""
    return [
        {
            "symbol": "000001",
            "name": "平安银行",
            "current_price": 10.5,
            "market_cap": 1000000000,
            "strength_score": 60.0,
            "trend_direction": 1,
        },
        {
            "symbol": "000002",
            "name": "万科A",
            "current_price": 8.5,
            "market_cap": 800000000,
            "strength_score": 55.0,
            "trend_direction": 0,
        },
    ]


@pytest_asyncio.fixture
async def db_with_sectors(test_session: AsyncSession, sample_sector_data):
    """
    创建包含板块数据的测试数据库

    将示例板块数据插入测试数据库。
    """
    from src.models.sector import Sector

    for sector_data in sample_sector_data:
        sector = Sector(**sector_data)
        test_session.add(sector)

    await test_session.commit()
    await test_session.refresh(test_session.query(Sector).first())

    yield test_session

    # 清理
    await test_session.rollback()


@pytest_asyncio.fixture
async def db_with_stocks(test_session: AsyncSession, sample_stock_data):
    """
    创建包含个股数据的测试数据库

    将示例个股数据插入测试数据库。
    """
    from src.models.stock import Stock

    for stock_data in sample_stock_data:
        stock = Stock(**stock_data)
        test_session.add(stock)

    await test_session.commit()

    yield test_session

    # 清理
    await test_session.rollback()
