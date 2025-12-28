"""
数据库缓存后端

基于数据库的简单缓存实现。
"""

import pickle
import asyncio
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cache import CacheEntry
from src.db.database import AsyncSessionLocal


class DatabaseCache:
    """
    基于数据库的简单缓存实现

    使用 CacheEntry 表存储缓存数据，支持 TTL 过期。
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._cleanup_interval = 3600  # 每小时清理一次过期缓存
        self._last_cleanup = None

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        session = AsyncSessionLocal()
        try:
            stmt = select(CacheEntry).where(
                CacheEntry.key == key,
                CacheEntry.expires_at > datetime.now()
            )
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()

            if entry:
                try:
                    return pickle.loads(entry.value)
                except (pickle.PickleError, EOFError):
                    return None
            return None
        finally:
            await session.close()

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认 1 小时
            session: 数据库会话（可选）

        Returns:
            是否成功
        """
        try:
            # 序列化值
            serialized_value = pickle.dumps(value)
            expires_at = datetime.now() + timedelta(seconds=ttl)

            # 使用提供的 session 或创建新的
            if session:
                await self._set_in_session(key, serialized_value, expires_at, session)
            else:
                new_session = AsyncSessionLocal()
                try:
                    await self._set_in_session(key, serialized_value, expires_at, new_session)
                finally:
                    await new_session.close()

            return True
        except (pickle.PickleError, Exception) as e:
            import logging
            logging.error(f"缓存设置失败: {e}")
            return False

    async def _set_in_session(
        self,
        key: str,
        serialized_value: bytes,
        expires_at: datetime,
        session: AsyncSession
    ):
        """在指定会话中设置缓存"""
        # 检查是否已存在
        stmt = select(CacheEntry).where(CacheEntry.key == key)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # 更新现有条目
            existing.value = serialized_value
            existing.expires_at = expires_at
        else:
            # 创建新条目
            import uuid
            entry = CacheEntry(
                id=str(uuid.uuid4()),
                key=key,
                value=serialized_value,
                expires_at=expires_at
            )
            session.add(entry)

        await session.commit()

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        session = AsyncSessionLocal()
        try:
            stmt = delete(CacheEntry).where(CacheEntry.key == key)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
        finally:
            await session.close()

    async def clear_pattern(self, pattern: str) -> int:
        """
        按模式清除缓存

        Args:
            pattern: 键模式（支持 SQL LIKE 语法）

        Returns:
            清除的缓存数量
        """
        session = AsyncSessionLocal()
        try:
            stmt = delete(CacheEntry).where(CacheEntry.key.like(pattern))
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount
        finally:
            await session.close()

    async def clear_all(self) -> int:
        """
        清除所有缓存

        Returns:
            清除的缓存数量
        """
        session = AsyncSessionLocal()
        try:
            stmt = delete(CacheEntry)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount
        finally:
            await session.close()

    async def cleanup_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的缓存数量
        """
        session = AsyncSessionLocal()
        try:
            stmt = delete(CacheEntry).where(
                CacheEntry.expires_at <= datetime.now()
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount
        finally:
            await session.close()

    async def get_many(self, keys: list[str]) -> Dict[str, Any]:
        """
        批量获取缓存

        Args:
            keys: 缓存键列表

        Returns:
            键值对字典
        """
        results = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                results[key] = value
        return results

    async def set_many(self, mapping: Dict[str, Any], ttl: int = 3600) -> int:
        """
        批量设置缓存

        Args:
            mapping: 键值对字典
            ttl: 过期时间（秒）

        Returns:
            成功设置的数量
        """
        count = 0
        for key, value in mapping.items():
            if await self.set(key, value, ttl):
                count += 1
        return count

    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在且未过期
        """
        return await self.get(key) is not None

    async def ttl(self, key: str) -> Optional[int]:
        """
        获取缓存剩余 TTL

        Args:
            key: 缓存键

        Returns:
            剩余秒数，如果不存在返回 None
        """
        session = AsyncSessionLocal()
        try:
            stmt = select(CacheEntry).where(
                CacheEntry.key == key,
                CacheEntry.expires_at > datetime.now()
            )
            result = await session.execute(stmt)
            entry = result.scalar_one_or_none()

            if entry:
                remaining = (entry.expires_at - datetime.now()).total_seconds()
                return max(0, int(remaining))
            return None
        finally:
            await session.close()
