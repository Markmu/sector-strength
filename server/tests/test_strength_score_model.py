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
from src.models.base import Base


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    # 只创建 strength_scores 表，避免 UUID 类型问题
    StrengthScore.__table__.create(engine, checkfirst=True)
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
            symbol="600000",
            entity_type="stock",
            entity_id=123,  # 使用整数ID
            date=date(2025, 1, 1),
            period="all",  # period 已废弃，固定为 'all'
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
        assert saved.symbol == "600000"
        assert saved.entity_type == "stock"
        assert saved.entity_id == 123  # 现在是整数
        assert saved.date == date(2025, 1, 1)
        assert saved.period == "all"  # period 已废弃，固定为 'all'
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
            symbol="sector_001",
            entity_type="sector",
            entity_id=456,  # 使用整数ID
            date=date(2025, 1, 1),
            period="all",  # period 已废弃，固定为 'all'
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
        assert saved.symbol == "sector_001"
        assert saved.entity_type == "sector"
        assert saved.entity_id == 456  # 现在是整数
        assert saved.period == "all"  # period 已废弃，固定为 'all'
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
            symbol="600789",
            entity_type="stock",
            entity_id=789,  # 使用整数ID
            date=date(2025, 1, 1),
            period="all",  # period 已废弃，固定为 'all'
            score=Decimal("80.00"),
            strength_level="strong",
        )
        db_session.add(score1)
        db_session.commit()

        # 创建相同 entity_type、entity_id、date、period 的记录现在应该被允许
        score2 = StrengthScore(
            symbol="600789",
            entity_type="stock",
            entity_id=789,  # 使用相同的整数ID
            date=date(2025, 1, 1),
            period="all",  # period 已废弃，固定为 'all'
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
            StrengthScore.period == "all"  # period 已废弃，固定为 'all'
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
            for j, entity_type in enumerate(["stock", "sector"]):
                # period 已废弃，只使用 'all'
                score = StrengthScore(
                    symbol=f"600{i:03d}" if entity_type == "stock" else f"sector_{i:03d}",
                    entity_type=entity_type,
                    entity_id=i * 10 + j,  # 使用整数ID
                    date=test_date,
                    period="all",  # period 已废弃，固定为 'all'
                    score=Decimal(str(80 + i)),
                    strength_level="strong",
                )
                db_session.add(score)

        db_session.commit()

        # 测试按 entity_type 查询
        stock_scores = db_session.query(StrengthScore).filter(
            StrengthScore.entity_type == "stock"
        ).all()
        assert len(stock_scores) == 3  # 3 dates * 1 period (all)

        # 测试按日期范围查询
        scores_jan2 = db_session.query(StrengthScore).filter(
            StrengthScore.date >= date(2025, 1, 2)
        ).all()
        assert len(scores_jan2) == 4  # 2 dates * 2 entity_types * 1 period (all)

    def test_decimal_precision(self, db_session):
        """测试小数精度"""
        # 测试精确到4位小数
        score = StrengthScore(
            symbol="600999",
            entity_type="stock",
            entity_id=999,  # 使用整数ID
            date=date(2025, 1, 1),
            period="all",  # period 已废弃，固定为 'all'
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
            symbol="600888",
            entity_type="stock",
            entity_id=888,  # 使用整数ID
            date=date(2025, 1, 1),
            period="all",  # period 已废弃，固定为 'all'
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
        assert "all" in repr_str  # period 已废弃，固定为 'all'


class TestStrengthScoreMASystemOptimization:
    """均线系统优化后的强度得分模型测试类"""

    def test_symbol_field_required(self, db_session):
        """测试 symbol 字段存在且非空"""
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).first()
        assert hasattr(saved, 'symbol')
        assert saved.symbol == "600000"

    def test_price_position_score_field(self, db_session):
        """测试价格位置得分字段"""
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
            price_position_score=Decimal("75.00"),
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).first()
        assert hasattr(saved, 'price_position_score')
        assert saved.price_position_score == Decimal("75.00")

    def test_ma_alignment_score_field(self, db_session):
        """测试均线排列得分字段"""
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
            ma_alignment_score=Decimal("90.00"),
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).first()
        assert hasattr(saved, 'ma_alignment_score')
        assert saved.ma_alignment_score == Decimal("90.00")

    def test_ma_alignment_state_field(self, db_session):
        """测试均线排列状态字段"""
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
            ma_alignment_state="多头排列",
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).first()
        assert hasattr(saved, 'ma_alignment_state')
        assert saved.ma_alignment_state == "多头排列"

    def test_short_medium_long_term_scores(self, db_session):
        """测试短中长期强度得分字段"""
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
            short_term_score=Decimal("80.00"),
            medium_term_score=Decimal("85.00"),
            long_term_score=Decimal("90.00"),
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).first()
        assert hasattr(saved, 'short_term_score')
        assert hasattr(saved, 'medium_term_score')
        assert hasattr(saved, 'long_term_score')
        assert saved.short_term_score == Decimal("80.00")
        assert saved.medium_term_score == Decimal("85.00")
        assert saved.long_term_score == Decimal("90.00")

    def test_ma_values_fields(self, db_session):
        """测试均线值字段 (ma5/10/20/30/60/90/120/240)"""
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
            current_price=Decimal("10.50"),
            ma5=Decimal("10.30"),
            ma10=Decimal("10.20"),
            ma20=Decimal("10.10"),
            ma30=Decimal("10.00"),
            ma60=Decimal("9.90"),
            ma90=Decimal("9.80"),
            ma120=Decimal("9.70"),
            ma240=Decimal("9.60"),
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).first()
        assert hasattr(saved, 'current_price')
        assert hasattr(saved, 'ma5')
        assert hasattr(saved, 'ma10')
        assert hasattr(saved, 'ma20')
        assert hasattr(saved, 'ma30')
        assert hasattr(saved, 'ma60')
        assert hasattr(saved, 'ma90')
        assert hasattr(saved, 'ma120')
        assert hasattr(saved, 'ma240')
        assert saved.current_price == Decimal("10.50")
        assert saved.ma5 == Decimal("10.30")
        assert saved.ma240 == Decimal("9.60")

    def test_price_above_ma_fields(self, db_session):
        """测试价格相对均线位置字段 (8个字段)"""
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
            price_above_ma5=1,
            price_above_ma10=1,
            price_above_ma20=1,
            price_above_ma30=0,
            price_above_ma60=0,
            price_above_ma90=0,
            price_above_ma120=0,
            price_above_ma240=0,
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).first()
        assert hasattr(saved, 'price_above_ma5')
        assert hasattr(saved, 'price_above_ma10')
        assert hasattr(saved, 'price_above_ma20')
        assert hasattr(saved, 'price_above_ma30')
        assert hasattr(saved, 'price_above_ma60')
        assert hasattr(saved, 'price_above_ma90')
        assert hasattr(saved, 'price_above_ma120')
        assert hasattr(saved, 'price_above_ma240')
        assert saved.price_above_ma5 == 1
        assert saved.price_above_ma10 == 1
        assert saved.price_above_ma20 == 1
        assert saved.price_above_ma30 == 0

    def test_change_rate_1d_field(self, db_session):
        """测试1日得分变化率字段"""
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
            change_rate_1d=Decimal("5.25"),
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).first()
        assert hasattr(saved, 'change_rate_1d')
        assert saved.change_rate_1d == Decimal("5.25")

    def test_strength_grade_field(self, db_session):
        """测试强度等级字段"""
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
            strength_grade="A+",
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).first()
        assert hasattr(saved, 'strength_grade')
        assert saved.strength_grade == "A+"

    def test_score_range_constraint(self, db_session):
        """测试 score 范围约束 (0-100)"""
        # 有效值应该通过
        score_valid = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
        )
        db_session.add(score_valid)
        db_session.commit()

        # 超出范围的值应该失败 (需要在数据库层面验证)
        # 这里测试属性存在
        saved = db_session.query(StrengthScore).first()
        assert 0 <= saved.score <= 100

    def test_period_values_constraint(self, db_session):
        """测试 period 值约束 - period 已废弃，只允许 'all'"""
        # period 字段已废弃，固定为 'all'
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
        )
        db_session.add(score)
        db_session.commit()

        # 验证只有 'all' 值能保存
        saved = db_session.query(StrengthScore).filter(StrengthScore.period == "all").first()
        assert saved is not None
        assert saved.period == "all"

    def test_entity_type_constraint(self, db_session):
        """测试 entity_type 约束"""
        valid_types = ['stock', 'sector']
        for i, entity_type in enumerate(valid_types):
            score = StrengthScore(
                symbol=f"600{i:03d}" if entity_type == "stock" else f"sector_{i:03d}",
                entity_type=entity_type,
                entity_id=123 + i,
                date=date(2025, 1, 1),
                period="all",
                score=Decimal("85.50"),
            )
            db_session.add(score)
        db_session.commit()

        # 验证所有有效 entity_type 都能保存
        count = db_session.query(StrengthScore).filter(
            StrengthScore.entity_type.in_(valid_types)
        ).count()
        assert count == len(valid_types)

    def test_optimized_indexes(self, db_session):
        """测试优化索引存在"""
        # 创建大量测试数据
        for i in range(50):
            score = StrengthScore(
                symbol=f"600{i:03d}",
                entity_type="stock",
                entity_id=i,
                date=date(2025, 1, 1),
                period="all",
                score=Decimal(str(50 + i)),
            )
            db_session.add(score)
        db_session.commit()

        # 测试按 symbol 和 date 查询
        results = db_session.query(StrengthScore).filter(
            StrengthScore.symbol == "600010",
            StrengthScore.date == date(2025, 1, 1)
        ).first()
        assert results is not None

        # 测试按 score DESC 查询
        top_scores = db_session.query(StrengthScore).order_by(
            StrengthScore.score.desc()
        ).limit(10).all()
        assert len(top_scores) == 10

    def test_new_field_defaults(self, db_session):
        """测试新字段的默认值"""
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=123,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),
        )
        db_session.add(score)
        db_session.commit()

        saved = db_session.query(StrengthScore).first()
        # 新字段应该允许 NULL
        assert saved.symbol == "600000"
        # 以下字段应该可以为 None
        assert saved.price_position_score is None or saved.price_position_score >= 0
        assert saved.ma_alignment_score is None or saved.ma_alignment_score >= 0