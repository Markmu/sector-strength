"""
基础 Repository 类

提供通用的数据访问操作，所有具体 Repository 继承此类。
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import uuid4

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    基础 Repository 类

    提供标准的 CRUD 操作，所有具体 Repository 应继承此类。

    Attributes:
        model: SQLAlchemy 模型类
        session: 异步数据库会话
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        初始化 Repository

        Args:
            model: SQLAlchemy 模型类
            session: 异步数据库会话
        """
        self.model = model
        self.session = session

    async def get(self, id: int) -> Optional[ModelType]:
        """
        根据 ID 获取单个实体

        Args:
            id: 实体 ID

        Returns:
            实体对象，不存在返回 None
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by(
        self, **filters: Dict[str, Any]
    ) -> Optional[ModelType]:
        """
        根据条件获取单个实体

        Args:
            **filters: 过滤条件（键值对）

        Returns:
            实体对象，不存在返回 None
        """
        stmt = select(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        **filters: Dict[str, Any],
    ) -> List[ModelType]:
        """
        获取实体列表

        Args:
            offset: 偏移量
            limit: 返回数量限制
            **filters: 过滤条件（键值对）

        Returns:
            实体列表
        """
        stmt = select(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        创建新实体

        Args:
            obj_in: 实体数据字典

        Returns:
            创建的实体对象
        """
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def bulk_create(
        self, objs_in: List[Dict[str, Any]]
    ) -> List[ModelType]:
        """
        批量创建实体

        Args:
            objs_in: 实体数据字典列表

        Returns:
            创建的实体对象列表
        """
        db_objs = [self.model(**obj_in) for obj_in in objs_in]
        self.session.add_all(db_objs)
        await self.session.flush()
        for db_obj in db_objs:
            await self.session.refresh(db_obj)
        return db_objs

    async def update(
        self,
        id: int,
        obj_in: Dict[str, Any],
    ) -> Optional[ModelType]:
        """
        更新实体

        Args:
            id: 实体 ID
            obj_in: 更新数据字典

        Returns:
            更新后的实体对象，不存在返回 None
        """
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**obj_in)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        """
        删除实体

        Args:
            id: 实体 ID

        Returns:
            是否删除成功
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def count(self, **filters: Dict[str, Any]) -> int:
        """
        统计实体数量

        Args:
            **filters: 过滤条件（键值对）

        Returns:
            实体数量
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar()

    async def exists(self, **filters: Dict[str, Any]) -> bool:
        """
        检查实体是否存在

        Args:
            **filters: 过滤条件（键值对）

        Returns:
            是否存在
        """
        count = await self.count(**filters)
        return count > 0
