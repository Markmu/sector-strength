"""
API 测试配置

提供测试 fixtures 和测试工具函数。
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from main import app


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


@pytest_asyncio.fixture
async def test_session():
    """
    创建测试数据库会话

    使用内存 SQLite 数据库进行测试。
    """
    # 创建测试引擎
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
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

    # 清理
    await engine.dispose()


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
