"""测试强度得分模型"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.strength_score import StrengthScore
from src.db.sync_database import Base


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestStrengthScore:
    """强度得分模型测试类"""

    def test_create_strength_score(self, db_session):
        """测试创建强度得分记录"""
        # 创建个股强度得分记录
        stock_strength = StrengthScore(
            entity_type="stock",
            entity_id=123,  # 使用整数ID
            date=date(2025, 1, 1),
            period="5d",
            score=Decimal("85.50"),
            rank=10,
            change_rate=Decimal("2.35"),
            strength_level="strong",
            ma5_score=Decimal("80.00"),
            ma10_score=Decimal("85.00"),
            ma20_score=Decimal("88.00"),
            volume_score=Decimal("90.00"),
            momentum_score=Decimal("82.50"),
        )
        db_session.add(stock_strength)
        db_session.commit()

        # 验证记录是否正确保存
        saved = db_session.query(StrengthScore).first()
        assert saved is not None
        assert saved.entity_type == "stock"
        assert saved.entity_id == 123  # 现在是整数
        assert saved.date == date(2025, 1, 1)
        assert saved.period == "5d"
        assert saved.score == Decimal("85.50")
        assert saved.rank == 10
        assert saved.change_rate == Decimal("2.35")
        assert saved.strength_level == "strong"
        assert saved.ma5_score == Decimal("80.00")
        assert saved.ma10_score == Decimal("85.00")
        assert saved.ma20_score == Decimal("88.00")
        assert saved.volume_score == Decimal("90.00")
        assert saved.momentum_score == Decimal("82.50")

    def test_create_sector_strength_score(self, db_session):
        """测试创建板块强度得分记录"""
        # 创建板块强度得分记录
        sector_strength = StrengthScore(
            entity_type="sector",
            entity_id=456,  # 使用整数ID
            date=date(2025, 1, 1),
            period="5d",
            score=Decimal("75.30"),
            rank=3,
            change_rate=Decimal("1.85"),
            strength_level="medium",
            avg_stock_score=Decimal("72.50"),
            strong_stock_ratio=Decimal("0.65"),
            up_stock_ratio=Decimal("0.75"),
            volume_ratio=Decimal("1.25"),
        )
        db_session.add(sector_strength)
        db_session.commit()

        # 验证记录是否正确保存
        saved = db_session.query(StrengthScore).filter(
            StrengthScore.entity_type == "sector"
        ).first()
        assert saved is not None
        assert saved.entity_type == "sector"
        assert saved.entity_id == 456  # 现在是整数
        assert saved.score == Decimal("75.30")
        assert saved.strength_level == "medium"
        assert saved.avg_stock_score == Decimal("72.50")
        assert saved.strong_stock_ratio == Decimal("0.65")
        assert saved.up_stock_ratio == Decimal("0.75")
        assert saved.volume_ratio == Decimal("1.25")

    def test_flexible_constraint(self, db_session):
        """测试灵活约束 - 移除了严格的唯一约束后"""
        # 创建第一条记录
        score1 = StrengthScore(
            entity_type="stock",
            entity_id=789,  # 使用整数ID
            date=date(2025, 1, 1),
            period="5d",
            score=Decimal("80.00"),
            strength_level="strong",
        )
        db_session.add(score1)
        db_session.commit()

        # 创建相同 entity_type、entity_id、date、period 的记录现在应该被允许
        score2 = StrengthScore(
            entity_type="stock",
            entity_id=789,  # 使用相同的整数ID
            date=date(2025, 1, 1),
            period="5d",
            score=Decimal("85.00"),
            strength_level="strong",
        )
        db_session.add(score2)
        db_session.commit()  # 现在应该成功，没有严格的唯一约束

        # 验证两条记录都存在
        records = db_session.query(StrengthScore).filter(
            StrengthScore.entity_type == "stock",
            StrengthScore.entity_id == 789,
            StrengthScore.date == date(2025, 1, 1),
            StrengthScore.period == "5d"
        ).all()
        assert len(records) == 2

    def test_index_fields(self, db_session):
        """测试索引字段"""
        # 创建多条测试记录
        test_dates = [
            date(2025, 1, 1),
            date(2025, 1, 2),
            date(2025, 1, 3),
        ]

        for i, test_date in enumerate(test_dates):
            for entity_type in ["stock", "sector"]:
                for period in ["5d", "10d"]:
                    score = StrengthScore(
                        entity_type=entity_type,
                        entity_id=i * 10,  # 使用整数ID
                        date=test_date,
                        period=period,
                        score=Decimal(str(80 + i)),
                        strength_level="strong",
                    )
                    db_session.add(score)

        db_session.commit()

        # 测试按 entity_type 查询
        stock_scores = db_session.query(StrengthScore).filter(
            StrengthScore.entity_type == "stock"
        ).all()
        assert len(stock_scores) == 6  # 3 dates * 2 periods

        # 测试按日期范围查询
        scores_jan2 = db_session.query(StrengthScore).filter(
            StrengthScore.date >= date(2025, 1, 2)
        ).all()
        assert len(scores_jan2) == 8  # 2 dates * 2 entity_types * 2 periods

    def test_decimal_precision(self, db_session):
        """测试小数精度"""
        # 测试精确到4位小数
        score = StrengthScore(
            entity_type="stock",
            entity_id=999,  # 使用整数ID
            date=date(2025, 1, 1),
            period="5d",
            score=Decimal("85.1234"),
            change_rate=Decimal("2.5678"),
            volume_ratio=Decimal("1.2345"),
            strength_level="strong",
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).filter(
            StrengthScore.entity_id == 999
        ).first()

        # 验证精度保持不变
        assert saved.score == Decimal("85.1234")
        assert saved.change_rate == Decimal("2.5678")
        assert saved.volume_ratio == Decimal("1.2345")

    def test_repr(self, db_session):
        """测试字符串表示"""
        score = StrengthScore(
            entity_type="stock",
            entity_id=888,  # 使用整数ID
            date=date(2025, 1, 1),
            period="5d",
            score=Decimal("80.00"),
            strength_level="strong",
        )
        db_session.add(score)
        db_session.commit()

        repr_str = repr(score)
        assert "StrengthScore" in repr_str
        assert "stock" in repr_str
        assert "888" in repr_str  # 现在是整数ID
        assert "2025-01-01" in repr_str
        assert "5d" in repr_str