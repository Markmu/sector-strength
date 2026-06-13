"""
股东监控组数据访问仓库

继承 BaseRepository，提供分组 + 规则联合查询、规则整体替换等自定义方法。
"""

from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.shareholder_group import ShareholderGroup, ShareholderGroupRule
from src.repositories.base import BaseRepository


class ShareholderGroupRepository(BaseRepository[ShareholderGroup]):
    """股东监控组仓库

    BaseRepository 提供 get / create / update / delete 等通用方法。
    本类扩展需要 join rules 的查询和规则替换场景。
    """

    def __init__(self, session: AsyncSession):
        super().__init__(ShareholderGroup, session)

    async def get_with_rules(self) -> list[ShareholderGroup]:
        """查询所有监控组及其关联规则（按 sort_order、id 排序）。

        Returns:
            ShareholderGroup 列表（rules 已通过 selectinload 预加载）
        """
        stmt = (
            select(ShareholderGroup)
            .options(selectinload(ShareholderGroup.rules))
            .order_by(ShareholderGroup.sort_order.asc(), ShareholderGroup.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_with_rules(self, group_id: int) -> ShareholderGroup:
        """查询单个监控组及其规则（不存在抛 NoResultFound）。

        Args:
            group_id: 监控组ID

        Returns:
            ShareholderGroup（rules 已预加载）

        Raises:
            LookupError: 分组不存在
        """
        stmt = (
            select(ShareholderGroup)
            .options(selectinload(ShareholderGroup.rules))
            .where(ShareholderGroup.id == group_id)
        )
        result = await self.session.execute(stmt)
        group = result.scalar_one_or_none()
        if group is None:
            raise LookupError(f"ShareholderGroup id={group_id} not found")
        return group

    async def get_by_name(self, name: str) -> Optional[ShareholderGroup]:
        """根据组名查询分组（用于唯一性校验）。

        Args:
            name: 组名

        Returns:
            ShareholderGroup 或 None
        """
        stmt = select(ShareholderGroup).where(ShareholderGroup.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def replace_rules(self, group_id: int, keywords: list[str]) -> list[str]:
        """整体替换分组的匹配规则（删除旧规则 → 插入新规则）。

        Args:
            group_id: 监控组ID
            keywords: 新关键词列表

        Returns:
            已写入的关键词列表
        """
        # 删除该组所有旧规则
        await self.session.execute(
            delete(ShareholderGroupRule).where(
                ShareholderGroupRule.group_id == group_id
            )
        )

        # 批量插入新规则（去重保序）
        seen: set[str] = set()
        unique_keywords: list[str] = []
        for kw in keywords:
            if kw and kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        for kw in unique_keywords:
            self.session.add(ShareholderGroupRule(group_id=group_id, keyword=kw))

        await self.session.flush()
        return unique_keywords
