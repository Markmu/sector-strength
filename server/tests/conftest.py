"""
测试配置文件

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
    """创建测试客户端"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def test_session():
    """创建测试数据库会话"""
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
