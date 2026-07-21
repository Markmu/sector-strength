"""测试股票独立表模型

覆盖 stock_daily_market_data / stock_moving_average_data / stock_strength_scores 三新模型：
- __tablename__ 正确
- 字段裁剪规则：无 entity_type；StockStrengthScore 无 period、无板块专属字段
- percentile 列存在（ADR-3）
- 基本 ORM 增删
"""

import pytest
from datetime import date
from decimal import Decimal
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.stock_daily_market_data import StockDailyMarketData
from src.models.stock_moving_average_data import StockMovingAverageData
from src.models.stock_strength_scores import StockStrengthScore
from src.models.base import Base


def _get_test_sync_db_url() -> str:
    test_url = os.getenv("TEST_DATABASE_URL")
    if not test_url:
        async_url = os.getenv("TEST_DATABASE_URL_ASYNC") or os.getenv("DATABASE_URL_ASYNC")
        if async_url:
            test_url = async_url.replace("+asyncpg", "")
    if not test_url:
        from src.core.settings import settings
        test_url = settings.sync_database_url
    if "sqlite" in test_url.lower():
        raise RuntimeError(
            f"SQLite is not allowed for tests. Got: {test_url}. "
            "Use PostgreSQL URL via TEST_DATABASE_URL or TEST_DATABASE_URL_ASYNC."
        )
    return test_url


@pytest.fixture
def db_session():
    """创建测试数据库会话（schema 隔离）"""
    db_url = _get_test_sync_db_url()
    schema = f"test_{uuid.uuid4().hex[:12]}"

    admin_engine = create_engine(db_url)
    with admin_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    admin_engine.dispose()

    engine = create_engine(
        db_url,
        connect_args={"options": f"-csearch_path={schema}"},
    )

    # 只创建本测试需要的三张表
    StockDailyMarketData.__table__.create(engine, checkfirst=True)
    StockMovingAverageData.__table__.create(engine, checkfirst=True)
    StockStrengthScore.__table__.create(engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()

    cleanup_engine = create_engine(db_url)
    with cleanup_engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    cleanup_engine.dispose()


class TestStockDailyMarketData:
    """股票日线行情数据模型测试"""

    def test_tablename(self):
        """测试表名正确"""
        assert StockDailyMarketData.__tablename__ == "stock_daily_market_data"

    def test_no_entity_type_column(self):
        """测试无 entity_type 列"""
        cols = StockDailyMarketData.__table__.columns
        assert "entity_type" not in cols
        assert "stock_id" in cols

    def test_create_record(self, db_session):
        """测试创建行情记录"""
        data = StockDailyMarketData(
            stock_id=123,
            symbol="600000",
            date=date(2025, 1, 1),
            open=Decimal("10.00"),
            high=Decimal("10.50"),
            low=Decimal("9.80"),
            close=Decimal("10.30"),
            volume=Decimal("1000000"),
            turnover=Decimal("15000000"),
            change=Decimal("0.30"),
            change_percent=Decimal("3.0000"),
        )
        db_session.add(data)
        db_session.commit()

        saved = db_session.query(StockDailyMarketData).first()
        assert saved is not None
        assert saved.stock_id == 123
        assert saved.symbol == "600000"
        assert saved.date == date(2025, 1, 1)
        assert saved.close == Decimal("10.30")
        assert saved.change_percent == Decimal("3.0000")


class TestStockMovingAverageData:
    """股票均线数据模型测试"""

    def test_tablename(self):
        """测试表名正确"""
        assert StockMovingAverageData.__tablename__ == "stock_moving_average_data"

    def test_no_entity_type_column(self):
        """测试无 entity_type 列"""
        cols = StockMovingAverageData.__table__.columns
        assert "entity_type" not in cols
        assert "stock_id" in cols

    def test_period_field_kept(self):
        """测试 period 业务字段保留（均线表 period 是真实业务字段）"""
        cols = StockMovingAverageData.__table__.columns
        assert "period" in cols

    def test_create_record(self, db_session):
        """测试创建均线记录"""
        ma = StockMovingAverageData(
            stock_id=123,
            symbol="600000",
            date=date(2025, 1, 1),
            period="5d",
            ma_value=Decimal("10.20"),
            price_ratio=Decimal("1.0200"),
            trend=Decimal("1.00"),
        )
        db_session.add(ma)
        db_session.commit()

        saved = db_session.query(StockMovingAverageData).first()
        assert saved is not None
        assert saved.stock_id == 123
        assert saved.period == "5d"
        assert saved.ma_value == Decimal("10.20")


class TestStockStrengthScore:
    """股票强度得分模型测试（最关键）"""

    def test_tablename(self):
        """测试表名正确"""
        assert StockStrengthScore.__tablename__ == "stock_strength_scores"

    def test_no_entity_type_column(self):
        """测试无 entity_type 列"""
        cols = StockStrengthScore.__table__.columns
        assert "entity_type" not in cols
        assert "stock_id" in cols

    def test_no_period_column(self):
        """测试无 period 列（已废弃）"""
        cols = StockStrengthScore.__table__.columns
        assert "period" not in cols

    def test_no_sector_specific_fields(self):
        """测试无板块专属字段"""
        cols = StockStrengthScore.__table__.columns
        assert "avg_stock_score" not in cols
        assert "strong_stock_ratio" not in cols
        assert "up_stock_ratio" not in cols
        assert "volume_ratio" not in cols

    def test_individual_dead_fields_kept(self):
        """测试个股死字段照搬保留"""
        cols = StockStrengthScore.__table__.columns
        assert "ma5_score" in cols
        assert "ma10_score" in cols
        assert "ma20_score" in cols
        assert "volume_score" in cols
        assert "momentum_score" in cols

    def test_percentile_column_exists(self):
        """测试 percentile 列存在（ADR-3 关键）"""
        assert hasattr(StockStrengthScore, "percentile")
        cols = StockStrengthScore.__table__.columns
        assert "percentile" in cols
        # 精度校验
        percentile_col = cols["percentile"]
        assert percentile_col.type.precision == 10
        assert percentile_col.type.scale == 4

    def test_create_record_with_percentile(self, db_session):
        """测试创建强度记录（含 percentile）"""
        score = StockStrengthScore(
            stock_id=123,
            symbol="600000",
            date=date(2025, 1, 1),
            score=Decimal("85.5000"),
            rank=10,
            percentile=Decimal("95.0000"),
            strength_level="strong",
            ma5_score=Decimal("80.0000"),
            momentum_score=Decimal("82.5000"),
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StockStrengthScore).first()
        assert saved is not None
        assert saved.stock_id == 123
        assert saved.symbol == "600000"
        assert saved.score == Decimal("85.5000")
        assert saved.percentile == Decimal("95.0000")
        assert saved.ma5_score == Decimal("80.0000")

    def test_score_range_constraint(self, db_session):
        """测试 score 范围约束 (0-100)"""
        score = StockStrengthScore(
            stock_id=456,
            symbol="600001",
            date=date(2025, 1, 1),
            score=Decimal("85.5000"),
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StockStrengthScore).first()
        assert 0 <= saved.score <= 100

    def test_unique_constraint(self, db_session):
        """测试 stock_id + date 唯一约束（新增硬化去重）"""
        score1 = StockStrengthScore(
            stock_id=789,
            symbol="600002",
            date=date(2025, 1, 1),
            score=Decimal("80.0000"),
        )
        db_session.add(score1)
        db_session.commit()

        # 同 stock_id + date 再插入应失败
        score2 = StockStrengthScore(
            stock_id=789,
            symbol="600002",
            date=date(2025, 1, 1),
            score=Decimal("85.0000"),
        )
        db_session.add(score2)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_repr(self):
        """测试字符串表示"""
        score = StockStrengthScore(
            stock_id=123,
            symbol="600000",
            date=date(2025, 1, 1),
            score=Decimal("85.5000"),
        )
        repr_str = repr(score)
        assert "StockStrengthScore" in repr_str
        assert "123" in repr_str  # stock_id
        assert "2025-01-01" in repr_str  # date
