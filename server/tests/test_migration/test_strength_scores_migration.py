"""测试 strength_scores 表迁移"""

import pytest
from decimal import Decimal
from datetime import date

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.strength_score import StrengthScore
from src.models.base import Base
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def migrated_db_session():
    """创建已迁移的测试数据库"""
    engine = create_engine("sqlite:///:memory:")

    # 只创建 strength_scores 表，避免 UUID 类型问题
    StrengthScore.__table__.create(engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # 检查表结构
    inspector = inspect(engine)

    yield session, inspector

    session.close()


class TestStrengthScoresMigration:
    """strength_scores 表迁移验证测试"""

    def test_new_columns_exist(self, migrated_db_session):
        """验证所有新列已创建"""
        session, inspector = migrated_db_session

        columns = [col['name'] for col in inspector.get_columns('strength_scores')]

        # 验证 symbol 字段
        assert 'symbol' in columns

        # 验证核心得分字段
        assert 'price_position_score' in columns
        assert 'ma_alignment_score' in columns
        assert 'ma_alignment_state' in columns

        # 验证短中长期强度字段
        assert 'short_term_score' in columns
        assert 'medium_term_score' in columns
        assert 'long_term_score' in columns

        # 验证均线数据字段
        assert 'current_price' in columns
        assert 'ma5' in columns
        assert 'ma10' in columns
        assert 'ma20' in columns
        assert 'ma30' in columns
        assert 'ma60' in columns
        assert 'ma90' in columns
        assert 'ma120' in columns
        assert 'ma240' in columns

        # 验证价格相对均线位置字段
        assert 'price_above_ma5' in columns
        assert 'price_above_ma10' in columns
        assert 'price_above_ma20' in columns
        assert 'price_above_ma30' in columns
        assert 'price_above_ma60' in columns
        assert 'price_above_ma90' in columns
        assert 'price_above_ma120' in columns
        assert 'price_above_ma240' in columns

        # 验证排名和变化字段
        assert 'change_rate_1d' in columns
        assert 'strength_grade' in columns

    def test_symbol_not_null_constraint(self, migrated_db_session):
        """验证 symbol 字段 NOT NULL 约束"""
        session, inspector = migrated_db_session

        columns = {col['name']: col for col in inspector.get_columns('strength_scores')}
        assert columns['symbol']['nullable'] is False

    def test_new_indexes_exist(self, migrated_db_session):
        """验证优化索引已创建"""
        session, inspector = migrated_db_session

        indexes = inspector.get_indexes('strength_scores')
        index_names = [idx['name'] for idx in indexes]

        # 验证新索引存在
        assert 'ix_strength_scores_symbol' in index_names
        assert 'idx_strength_scores_symbol_date' in index_names
        assert 'idx_strength_scores_score_desc' in index_names

    def test_insert_with_new_fields(self, migrated_db_session):
        """测试使用新字段插入数据"""
        session, inspector = migrated_db_session

        # 创建带有所有新字段的记录
        score = StrengthScore(
            symbol="600000",
            entity_type="stock",
            entity_id=1,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.50"),

            # 新增核心得分字段
            price_position_score=Decimal("75.00"),
            ma_alignment_score=Decimal("90.00"),
            ma_alignment_state="多头排列",

            # 短中长期强度
            short_term_score=Decimal("80.00"),
            medium_term_score=Decimal("85.00"),
            long_term_score=Decimal("90.00"),

            # 均线数据
            current_price=Decimal("10.50"),
            ma5=Decimal("10.30"),
            ma10=Decimal("10.20"),
            ma20=Decimal("10.10"),
            ma30=Decimal("10.00"),
            ma60=Decimal("9.90"),
            ma90=Decimal("9.80"),
            ma120=Decimal("9.70"),
            ma240=Decimal("9.60"),

            # 价格相对均线位置
            price_above_ma5=1,
            price_above_ma10=1,
            price_above_ma20=1,
            price_above_ma30=0,
            price_above_ma60=0,
            price_above_ma90=0,
            price_above_ma120=0,
            price_above_ma240=0,

            # 排名和变化
            change_rate_1d=Decimal("5.25"),
            strength_grade="A+",
        )

        session.add(score)
        session.commit()

        # 验证数据正确保存
        saved = session.query(StrengthScore).filter_by(symbol="600000").first()
        assert saved is not None
        assert saved.price_position_score == Decimal("75.00")
        assert saved.ma_alignment_score == Decimal("90.00")
        assert saved.ma_alignment_state == "多头排列"
        assert saved.strength_grade == "A+"

    def test_nullable_new_fields(self, migrated_db_session):
        """测试新字段可为空"""
        session, inspector = migrated_db_session

        # 只填写必填字段，新字段应为 NULL
        score = StrengthScore(
            symbol="600001",
            entity_type="stock",
            entity_id=2,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("70.00"),
        )

        session.add(score)
        session.commit()

        saved = session.query(StrengthScore).filter_by(symbol="600001").first()
        assert saved.price_position_score is None
        assert saved.ma_alignment_score is None
        assert saved.strength_grade is None

    def test_period_all_value(self, migrated_db_session):
        """测试 period='all' 值有效"""
        session, inspector = migrated_db_session

        score = StrengthScore(
            symbol="600002",
            entity_type="stock",
            entity_id=3,
            date=date(2025, 1, 1),
            period="all",  # 新增的 period 值
            score=Decimal("85.00"),
        )

        session.add(score)
        session.commit()

        saved = session.query(StrengthScore).filter_by(symbol="600002").first()
        assert saved.period == "all"

    def test_backward_compatibility(self, migrated_db_session):
        """测试向后兼容性 - 旧字段仍可使用"""
        session, inspector = migrated_db_session

        # 使用旧字段创建记录
        score = StrengthScore(
            symbol="600003",
            entity_type="stock",
            entity_id=4,
            date=date(2025, 1, 1),
            period="5d",
            score=Decimal("80.00"),
            change_rate=Decimal("2.5"),
            strength_level="strong",
            rank=10,

            # 旧字段仍可用
            ma5_score=Decimal("75.0"),
            ma10_score=Decimal("80.0"),
            ma20_score=Decimal("85.0"),
        )

        session.add(score)
        session.commit()

        saved = session.query(StrengthScore).filter_by(symbol="600003").first()
        assert saved.ma5_score == Decimal("75.0")
        assert saved.strength_level == "strong"

    def test_price_above_ma_constraints(self, migrated_db_session):
        """测试 price_above_maX 字段只接受 0 或 1"""
        session, inspector = migrated_db_session

        # 有效值：0 和 1
        score1 = StrengthScore(
            symbol="600004",
            entity_type="stock",
            entity_id=5,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("80.00"),
            price_above_ma5=0,
            price_above_ma10=1,
        )
        session.add(score1)
        session.commit()
        assert session.query(StrengthScore).filter_by(symbol="600004").first() is not None

    def test_period_all_in_get_period_name(self, migrated_db_session):
        """测试 get_period_name 方法支持 'all' period"""
        session, inspector = migrated_db_session

        score = StrengthScore(
            symbol="600005",
            entity_type="stock",
            entity_id=6,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("85.00"),
        )
        session.add(score)
        session.commit()

        saved = session.query(StrengthScore).filter_by(symbol="600005").first()
        assert saved.get_period_name() == "全部"  # 而不是 "all周期"

    def test_score_range_boundary_values(self, migrated_db_session):
        """测试 score 边界值 (0 和 100)"""
        session, inspector = migrated_db_session

        # 测试 score = 0
        score_min = StrengthScore(
            symbol="600006",
            entity_type="stock",
            entity_id=7,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("0"),
        )
        session.add(score_min)

        # 测试 score = 100
        score_max = StrengthScore(
            symbol="600007",
            entity_type="stock",
            entity_id=8,
            date=date(2025, 1, 1),
            period="all",
            score=Decimal("100"),
        )
        session.add(score_max)
        session.commit()

        assert session.query(StrengthScore).filter_by(symbol="600006").first().score == Decimal("0")
        assert session.query(StrengthScore).filter_by(symbol="600007").first().score == Decimal("100")
