"""add_fund_portfolio_period_symbol_index

Revision ID: 4b8668ae3d1d
Revises: 414f872958de
Create Date: 2026-06-24 10:00:00.000000

非阻塞索引优化（08 期 plan-01 §3 #10，arch-check 标注）。

新增索引 ix_fund_portfolio_period_symbol (report_period, stock_symbol)：
让扎堆度聚合 SQL（WHERE report_period = :latest GROUP BY stock_symbol）走索引前缀扫描，
提升 15 万行级别实时聚合性能。

现有 ix_fund_portfolio_symbol_period (stock_symbol, report_period) 索引前缀为 stock_symbol，
对 WHERE report_period + GROUP BY stock_symbol 查询效率低（report_period 在第二位）。
新索引不替换旧索引（旧索引用于其他查询路径如 reverse-lookup）。
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4b8668ae3d1d'
down_revision: Union[str, Sequence[str], None] = '414f872958de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = 'ix_fund_portfolio_period_symbol'
TABLE_NAME = 'fund_portfolio'
COLUMNS = ['report_period', 'stock_symbol']


def upgrade() -> None:
    op.create_index(INDEX_NAME, TABLE_NAME, COLUMNS)


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
