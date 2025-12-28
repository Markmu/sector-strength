"""登录速率限制"""

from datetime import datetime, timedelta
from typing import Dict
from collections import defaultdict
import asyncio
from src.core.settings import settings

# 内存存储登录尝试
# 在生产环境中应该使用Redis等分布式缓存
login_attempts: Dict[str, list] = defaultdict(list)
lock = asyncio.Lock()


async def rate_limit_login(email: str, max_attempts: int = 5, window_minutes: int = 5) -> bool:
    """
    检查登录速率限制

    Args:
        email: 用户邮箱
        max_attempts: 最大尝试次数
        window_minutes: 时间窗口（分钟）

    Returns:
        bool: 是否允许登录
    """
    async with lock:
        now = datetime.utcnow()

        # 清理过期的登录尝试
        attempts = login_attempts[email]
        attempts[:] = [
            attempt_time for attempt_time in attempts
            if now - attempt_time < timedelta(minutes=window_minutes)
        ]

        # 检查是否超过限制
        if len(attempts) >= max_attempts:
            return False

        # 记录新的登录尝试
        attempts.append(now)
        return True


async def is_account_locked(email: str) -> bool:
    """
    检查账户是否被锁定

    Args:
        email: 用户邮箱

    Returns:
        bool: 是否被锁定
    """
    async with lock:
        attempts = login_attempts[email]
        now = datetime.utcnow()

        # 如果最近30分钟内有5次以上失败尝试，锁定账户30分钟
        recent_failures = [
            attempt for attempt in attempts
            if now - attempt < timedelta(minutes=30)
        ]

        if len(recent_failures) >= 5:
            return True

        return False


def clear_failed_attempts(email: str):
    """
    清除失败尝试（如登录成功）

    Args:
        email: 用户邮箱
    """
    login_attempts[email] = []