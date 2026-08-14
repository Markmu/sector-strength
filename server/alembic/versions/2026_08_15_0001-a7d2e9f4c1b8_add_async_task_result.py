"""add async task fencing columns

Revision ID: a7d2e9f4c1b8
Revises: e5c1f3a90b2d
Create Date: 2026-08-15 00:01:00.000000

为 A股全市场量价指标（第 16 期 plan-04 异步任务 fencing 基础设施）给既有
``async_tasks`` 表追加 4 个 nullable 列，全部仅由 ``sync_market_metrics`` 新路径读写：
- ``result`` JSON：结构化结果（``MarketMetricsTaskResult``，首因/部分失败计数与 dateResults）
- ``cancel_requested_at``：取消请求时间（首因胜出，running 协程退出后才 finalize）
- ``timeout_requested_at``：超时请求时间（对称条件更新）
- ``executor_acquisition_token``：执行器 acquisition fencing 身份（每次成功取得专属 owner
  lock 都重新生成的 UUID）

其他约 28 类任务保持这些字段为 NULL 且沿用原有状态语义。down_revision 指向 plan-03
后补丁迁移 ``e5c1f3a90b2d``（迁移链 head）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d2e9f4c1b8'
down_revision: Union[str, Sequence[str], None] = 'e5c1f3a90b2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: async_tasks 追加 4 个 nullable fencing 列。"""
    op.add_column(
        'async_tasks',
        sa.Column(
            'result',
            sa.JSON(),
            nullable=True,
            comment='结构化结果（仅 sync_market_metrics 读写，透传 MarketMetricsTaskResult）',
        ),
    )
    op.add_column(
        'async_tasks',
        sa.Column(
            'cancel_requested_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='取消请求时间（sync_market_metrics 首因胜出）',
        ),
    )
    op.add_column(
        'async_tasks',
        sa.Column(
            'timeout_requested_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='超时请求时间（sync_market_metrics 首因胜出）',
        ),
    )
    op.add_column(
        'async_tasks',
        sa.Column(
            'executor_acquisition_token',
            sa.String(length=36),
            nullable=True,
            comment='执行器 acquisition token（sync_market_metrics fencing 身份）',
        ),
    )


def downgrade() -> None:
    """Downgrade schema: 移除 async_tasks 的 4 个 fencing 列。"""
    op.drop_column('async_tasks', 'executor_acquisition_token')
    op.drop_column('async_tasks', 'timeout_requested_at')
    op.drop_column('async_tasks', 'cancel_requested_at')
    op.drop_column('async_tasks', 'result')
