"""fix_hk_stock_codes_to_5_digits

Revision ID: f5e4d3c2b1a0
Revises: 4b8668ae3d1d
Create Date: 2026-06-25 10:00:00.000000

港股代码规范化5位（08 期数据修正）。

Tushare fund_portfolio 的港股代码为4位（如 0700 腾讯、0001 长和），
标准港股代码为5位（00700、00001）。一次性 UPDATE 将 <5 位的纯数字代码
lpad 到5位，保证与标准港股代码体系匹配（前端规范显示 / 将来匹配港股数据）。

A 股 6 位代码不受影响（WHERE length < 5）。
同步层 data_init_fund.py 已加 lpad5 逻辑，防止未来同步又存4位。
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f5e4d3c2b1a0'
down_revision: Union[str, Sequence[str], None] = '4b8668ae3d1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE fund_portfolio
        SET stock_symbol = lpad(stock_symbol, 5, '0')
        WHERE length(stock_symbol) < 5
          AND stock_symbol ~ '^[0-9]+$'
        """
    )


def downgrade() -> None:
    # 数据规范化不可逆（lpad 后无法还原原始位数），downgrade 为 no-op
    pass
