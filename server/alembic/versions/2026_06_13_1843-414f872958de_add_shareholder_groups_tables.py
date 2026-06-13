"""add_shareholder_groups_tables

Revision ID: 414f872958de
Revises: 2a1ba1aca13f
Create Date: 2026-06-13 18:43:24.443895

新增股东监控组两张表 + 5 个预定义监控组的种子数据（含关键词）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '414f872958de'
down_revision: Union[str, Sequence[str], None] = '2a1ba1aca13f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 预定义监控组及关键词（与 src.services.shareholder_group_service.PREDEFINED_GROUPS 一致）
_PREDEFINED_GROUPS = [
    {
        "name": "国家队",
        "description": "汇金、证金等国家队资金",
        "sort_order": 1,
        "keywords": [
            "中央汇金",
            "中国证券金融",
            "国家外汇管理局",
            "国新投资",
            "基本养老保险基金",
        ],
    },
    {
        "name": "外资投行",
        "description": "著名外资投资银行",
        "sort_order": 2,
        "keywords": [
            "高盛",
            "摩根士丹利",
            "摩根大通",
            "瑞士银行",
            "美林",
            "花旗",
            "渣打",
        ],
    },
    {
        "name": "社保基金",
        "description": "全国社会保障基金",
        "sort_order": 3,
        "keywords": ["全国社保基金"],
    },
    {
        "name": "保险公司",
        "description": "保险资金",
        "sort_order": 4,
        "keywords": [
            "中国人寿",
            "中国平安",
            "中国太保",
            "新华保险",
            "泰康资产",
        ],
    },
    {
        "name": "私募基金",
        "description": "知名私募机构",
        "sort_order": 5,
        "keywords": [
            "高毅资产",
            "景林资产",
            "淡水泉",
            "重阳投资",
            "幻方量化",
            "九坤投资",
        ],
    },
]


def upgrade() -> None:
    """Upgrade schema: 建表 + 写入种子数据（幂等）。"""
    # 1) shareholder_groups
    op.create_table(
        'shareholder_groups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='组名（唯一）'),
        sa.Column('description', sa.Text(), nullable=True, comment='描述'),
        sa.Column('sort_order', sa.Integer(), nullable=False, comment='排序权重'),
        sa.Column('is_system', sa.Boolean(), nullable=False, comment='是否系统预定义'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # 2) shareholder_group_rules
    op.create_table(
        'shareholder_group_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='主键ID'),
        sa.Column('group_id', sa.Integer(), nullable=False, comment='所属监控组ID'),
        sa.Column('keyword', sa.String(length=200), nullable=False, comment='匹配关键词'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.ForeignKeyConstraint(['group_id'], ['shareholder_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sgr_group_id', 'shareholder_group_rules', ['group_id'], unique=False)

    # 3) 种子数据：5 个预定义监控组及其关键词（ON CONFLICT DO NOTHING 保证幂等）
    for group in _PREDEFINED_GROUPS:
        # 插入分组（name 冲突时跳过）
        op.execute(
            sa.text(
                """
                INSERT INTO shareholder_groups (name, description, sort_order, is_system)
                VALUES (:name, :description, :sort_order, TRUE)
                ON CONFLICT (name) DO NOTHING
                """
            ).bindparams(
                name=group["name"],
                description=group["description"],
                sort_order=group["sort_order"],
            )
        )
        # 查询该分组的 id（含已存在的）
        result = op.get_bind().execute(
            sa.text("SELECT id FROM shareholder_groups WHERE name = :name").bindparams(
                name=group["name"]
            )
        )
        group_row = result.first()
        if group_row is None:
            continue
        group_id = group_row[0]

        # 插入该组的关键词（同组同关键词冲突时跳过，幂等）
        for keyword in group["keywords"]:
            op.execute(
                sa.text(
                    """
                    INSERT INTO shareholder_group_rules (group_id, keyword)
                    VALUES (:group_id, :keyword)
                    ON CONFLICT DO NOTHING
                    """
                ).bindparams(group_id=group_id, keyword=keyword)
            )


def downgrade() -> None:
    """Downgrade schema: 删除两张表（CASCADE 自动清理规则）。"""
    op.drop_index('ix_sgr_group_id', table_name='shareholder_group_rules')
    op.drop_table('shareholder_group_rules')
    op.drop_table('shareholder_groups')
