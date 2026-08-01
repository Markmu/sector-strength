"""rebuild etf_basic table for etf_basic 接口

Revision ID: c4f2a1b9e7d3
Revises: 1bb0230382a3
Create Date: 2026-08-01 00:01:00

ETF 基础信息同步改用 Tushare 独立的 ``etf_basic`` 接口（list_status='L' 仅上市），
跟踪指数用官方 index_code / index_name 直接入库，不再做 benchmark 文本归类。

本迁移删除旧 etf_basic 表（含 management/fund_type/benchmark/category/status/
market 等字段）并按新结构重建。旧数据丢弃，后续重新同步即可。etf_daily 不动
（ts_code 关联键不变，换接口后旧 daily 数据仍可用）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f2a1b9e7d3'
down_revision: Union[str, Sequence[str], None] = '1bb0230382a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: drop 旧 etf_basic + 按新结构重建。"""
    # 1. 删除旧 etf_basic（含旧索引）
    op.drop_index('idx_etf_basic_category', table_name='etf_basic')
    op.drop_table('etf_basic')

    # 2. 按新结构重建 etf_basic：来源 Tushare etf_basic 接口，跟踪指数官方直取
    op.create_table(
        'etf_basic',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('ts_code', sa.String(length=20), nullable=False,
                  comment='TS代码，唯一标识'),
        sa.Column('name', sa.String(length=100), nullable=True,
                  comment='ETF简称（etf_basic.csname）'),
        sa.Column('full_name', sa.String(length=200), nullable=True,
                  comment='基金全称（etf_basic.cname）'),
        sa.Column('index_code', sa.String(length=20), nullable=True,
                  comment='跟踪指数代码（etf_basic.index_code）'),
        sa.Column('index_name', sa.String(length=100), nullable=True,
                  comment='跟踪指数名（etf_basic.index_name）'),
        sa.Column('list_date', sa.Date(), nullable=True, comment='上市日期'),
        sa.Column('setup_date', sa.Date(), nullable=True, comment='设立日期'),
        sa.Column('list_status', sa.String(length=10), nullable=True,
                  comment='存续状态: L上市 D退市 P待上市'),
        sa.Column('exchange', sa.String(length=10), nullable=True,
                  comment='交易所: SH/SZ'),
        sa.Column('mgr_name', sa.String(length=100), nullable=True,
                  comment='基金管理人简称'),
        sa.Column('etf_type', sa.String(length=20), nullable=True,
                  comment='投资通道类型（境内/QDII）'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                  comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ts_code'),
    )
    op.create_index('idx_etf_basic_index_code', 'etf_basic', ['index_code'],
                    unique=False)


def downgrade() -> None:
    """Downgrade schema: 恢复旧 etf_basic 结构（数据不恢复）。"""
    op.drop_index('idx_etf_basic_index_code', table_name='etf_basic')
    op.drop_table('etf_basic')

    # 恢复旧结构（仅 schema，数据已丢）
    op.create_table(
        'etf_basic',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='主键ID'),
        sa.Column('ts_code', sa.String(length=20), nullable=False,
                  comment='TS代码，唯一标识'),
        sa.Column('name', sa.String(length=100), nullable=True, comment='ETF名称'),
        sa.Column('management', sa.String(length=200), nullable=True, comment='管理人'),
        sa.Column('fund_type', sa.String(length=50), nullable=True, comment='基金类型'),
        sa.Column('list_date', sa.Date(), nullable=True, comment='上市日期'),
        sa.Column('benchmark', sa.String(length=500), nullable=True,
                  comment='业绩比较基准（跟踪指数文本）'),
        sa.Column('index_name', sa.String(length=100), nullable=True,
                  comment='归集后的跟踪指数名（归集器产出）'),
        sa.Column('category', sa.String(length=20), nullable=True,
                  comment='指数分类: broad/industry/other'),
        sa.Column('status', sa.String(length=20), nullable=True,
                  comment='状态: I 发行中 L 已上市 E 到期'),
        sa.Column('market', sa.String(length=20), nullable=True,
                  comment='市场类型: E 场内'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True,
                  comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ts_code'),
    )
    op.create_index('idx_etf_basic_category', 'etf_basic', ['category'],
                    unique=False)
