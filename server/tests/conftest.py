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


# 别名，兼容性
@pytest_asyncio.fixture
async def async_client(client: AsyncClient):
    """创建测试客户端（别名）"""
    yield client


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


@pytest_asyncio.fixture
async def db_session(test_session: AsyncSession):
    """数据库会话（别名）"""
    yield test_session


# Sample 数据 fixtures
@pytest_asyncio.fixture
async def sample_sectors(test_session: AsyncSession):
    """创建示例板块数据"""
    from src.models.sector import Sector
    from datetime import datetime

    sectors = [
        Sector(
            name='新能源',
            code='IND001',
            type='industry',
            description='新能源行业',
            strength_score=80.0,
        ),
        Sector(
            name='人工智能',
            code='CON001',
            type='concept',
            description='人工智能概念',
            strength_score=68.0,
        ),
        Sector(
            name='金融',
            code='IND002',
            type='industry',
            description='金融行业',
            strength_score=55.0,
        ),
    ]

    test_session.add_all(sectors)
    await test_session.commit()

    # 刷新以获取 ID
    for sector in sectors:
        await test_session.refresh(sector)

    return sectors


@pytest_asyncio.fixture
async def sample_strength_scores(test_session: AsyncSession, sample_sectors):
    """创建示例强度得分数据"""
    from src.models.strength_score import StrengthScore
    from datetime import date

    scores = [
        StrengthScore(
            entity_type='sector',
            entity_id=sample_sectors[0].id,
            symbol=sample_sectors[0].code,
            date=date.today(),
            period='all',
            score=80.0,
            short_term_score=75.5,
            medium_term_score=82.3,
            long_term_score=88.0,
            strong_stock_ratio=0.7,
            strength_grade='A',
            price_position_score=75.0,
            ma_alignment_score=85.0,
            ma_alignment_state='bullish',
        ),
        StrengthScore(
            entity_type='sector',
            entity_id=sample_sectors[1].id,
            symbol=sample_sectors[1].code,
            date=date.today(),
            period='all',
            score=68.0,
            short_term_score=65.2,
            medium_term_score=70.8,
            long_term_score=72.0,
            strong_stock_ratio=None,  # 测试缺失数据
            strength_grade='B+',
            price_position_score=65.0,
            ma_alignment_score=70.0,
            ma_alignment_state='neutral',
        ),
        StrengthScore(
            entity_type='sector',
            entity_id=sample_sectors[2].id,
            symbol=sample_sectors[2].code,
            date=date.today(),
            period='all',
            score=55.0,
            short_term_score=50.0,
            medium_term_score=58.0,
            long_term_score=60.0,
            strong_stock_ratio=0.3,
            strength_grade='B',
            price_position_score=50.0,
            ma_alignment_score=55.0,
            ma_alignment_state='bearish',
        ),
    ]

    test_session.add_all(scores)
    await test_session.commit()

    return scores


@pytest_asyncio.fixture
async def sample_sectors_with_missing(test_session: AsyncSession):
    """创建用于测试缺失数据的板块"""
    from src.models.sector import Sector

    sector = Sector(
        name='测试板块',
        code='TEST001',
        type='industry',
        description='测试板块',
        strength_score=50.0,
    )

    test_session.add(sector)
    await test_session.commit()
    await test_session.refresh(sector)

    return [sector]


@pytest_asyncio.fixture
async def sample_strength_scores_missing(test_session: AsyncSession, sample_sectors_with_missing):
    """创建用于测试缺失数据的强度得分"""
    from src.models.strength_score import StrengthScore
    from datetime import date

    score = StrengthScore(
        entity_type='sector',
        entity_id=sample_sectors_with_missing[0].id,
        symbol=sample_sectors_with_missing[0].code,
        date=date.today(),
        period='all',
        score=50.0,
        short_term_score=45.0,
        medium_term_score=50.0,
        long_term_score=None,  # 测试缺失
        strong_stock_ratio=None,  # 测试缺失
        strength_grade='B',
        price_position_score=50.0,
        ma_alignment_score=48.0,
        ma_alignment_state='bearish',
    )

    test_session.add(score)
    await test_session.commit()

    return [score]
