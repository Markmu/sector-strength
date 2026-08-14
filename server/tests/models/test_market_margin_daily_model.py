"""MarketMarginDaily 模型元数据断言测试（第 17 期 plan-01）

纯元数据测试（不连库）：断言表名、trade_date 唯一约束与索引、六指标列
Numeric(20,2)、trade_date 非空、双时间戳列存在，以及 models/__init__.py
注册导出（``from src.models import MarketMarginDaily`` 可直接导入）。
"""

from sqlalchemy import Date, DateTime, Numeric

from src.models import MarketMarginDaily
from src.models.base import Base


class TestMarketMarginDailyModel:
    """market_margin_daily 模型元数据断言（spec REQ-2 存储契约）"""

    def test_tablename(self):
        """表名为 market_margin_daily"""
        assert MarketMarginDaily.__tablename__ == "market_margin_daily"

    def test_registered_in_base_metadata(self):
        """表已注册到 Base.metadata（alembic autogenerate 可见）"""
        assert "market_margin_daily" in Base.metadata.tables
        table = Base.metadata.tables["market_margin_daily"]
        assert table is MarketMarginDaily.__table__

    def test_trade_date_unique_constraint(self):
        """trade_date 唯一约束名：uq_market_margin_daily_trade_date"""
        table = MarketMarginDaily.__table__
        uq_names = {c.name for c in table.constraints if c.__class__.__name__ == "UniqueConstraint"}
        assert "uq_market_margin_daily_trade_date" in uq_names

    def test_trade_date_index(self):
        """trade_date 索引名：idx_market_margin_daily_trade_date"""
        index_names = {ix.name for ix in MarketMarginDaily.__table__.indexes}
        assert "idx_market_margin_daily_trade_date" in index_names

    def test_trade_date_not_nullable(self):
        """trade_date 不可空（每交易日唯一一行的锚点列）"""
        trade_date = MarketMarginDaily.__table__.columns["trade_date"]
        assert trade_date.nullable is False
        assert isinstance(trade_date.type, Date)

    def test_six_indicator_columns_numeric_20_2(self):
        """六指标列与 tushare margin 字段同名，全部 Numeric(20,2)、nullable"""
        expected = ["rzye", "rqye", "rzmre", "rzche", "rqmcl", "rzrqye"]
        table = MarketMarginDaily.__table__
        for name in expected:
            assert name in table.columns, f"缺少指标列 {name}"
            col = table.columns[name]
            assert isinstance(col.type, Numeric), f"{name} 应为 Numeric"
            assert col.type.precision == 20, f"{name} precision 应为 20"
            assert col.type.scale == 2, f"{name} scale 应为 2"
            assert col.nullable is True, f"{name} 应允许 NULL（聚合失败守卫由 plan-03 承担）"

    def test_rqyl_not_stored(self):
        """rqyl（融券余量）不入库（spec REQ-2 冻结决策）"""
        assert "rqyl" not in MarketMarginDaily.__table__.columns

    def test_timestamp_columns(self):
        """created_at / updated_at 存在且为 timezone-aware DateTime"""
        table = MarketMarginDaily.__table__
        for name in ("created_at", "updated_at"):
            assert name in table.columns, f"缺少时间戳列 {name}"
            col = table.columns[name]
            assert isinstance(col.type, DateTime)
            assert col.type.timezone is True

    def test_id_primary_key(self):
        """id 为 Integer 自增主键"""
        pk_cols = list(MarketMarginDaily.__table__.primary_key.columns)
        assert len(pk_cols) == 1
        assert pk_cols[0].name == "id"
